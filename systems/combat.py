"""
Combat system - damage calculation, attack resolution, and death handling.

Public API
----------
calculate_damage(attacker, defender, world)
    Compute the damage value for one attack using the full formula.

resolve_attack(attacker, defender, world, bus)
    Execute one attack, apply the damage, and publish events.
    Returns ``True`` if the defender died.

run_combat_round(player, enemy, world, bus)
    Execute a full round: determine initiative, each combatant attacks
    once (in order), and return ``"player_won"``, ``"player_died"``, or
    ``"ongoing"``.

process_status_effects(entity, world, bus)
    Tick all active status effects on an entity for one turn.

apply_status_effect(entity, effect, world, bus)
    Attach a :class:`~components.combat.StatusEffect` to an entity and
    publish the appropriate event.

Damage formula
--------------
    raw       = base_attack + STR_modifier + equipment_attack_bonus
                + attack_status_modifiers
    final     = max(1, int((raw - total_defense) * variance))
    variance  = random.uniform(0.85, 1.15)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.combat import Health, Stats, CombatStats, StatusEffects, StatusEffect
from components.inventory import Equipment, ItemData
from components.ai import AIBehavior
from components.identity import Identity
from engine.event_bus import (
    EntityDamaged, EntityDied, EntityHealed, CombatStarted,
    CombatEnded, MessagePosted, StatusEffectApplied, StatusEffectExpired,
)


def calculate_damage(
    attacker: int,
    defender: int,
    world: "World",
    is_player_attacking: bool = True,
) -> int:
    """
    Damage formula:
      raw = base_attack + str_modifier + equipment_attack_bonus + attack_status_modifier
      mitigated = raw - (base_defense + equipment_defense_bonus + defense_status_modifier)
      final = max(1, mitigated)  -- always deal at least 1 damage
    """
    cs = world.get_component(attacker, CombatStats)
    stats = world.get_component(attacker, Stats)
    eq = world.get_component(attacker, Equipment)
    sfx = world.get_component(attacker, StatusEffects)

    raw = (cs.total_attack if cs else 5)
    if stats:
        raw += stats.str_modifier
    if eq:
        raw += eq.total_attack_bonus(world)
    if sfx:
        raw += sfx.attack_modifier()

    # Defender mitigation
    def_cs = world.get_component(defender, CombatStats)
    def_eq = world.get_component(defender, Equipment)
    def_sfx = world.get_component(defender, StatusEffects)

    mitigation = (def_cs.total_defense if def_cs else 2)
    if def_eq:
        mitigation += def_eq.total_defense_bonus(world)
    if def_sfx:
        mitigation += def_sfx.defense_modifier()

    # Small random variance (±15%)
    variance = random.uniform(0.85, 1.15)
    final = max(1, int((raw - mitigation) * variance))
    return final


def resolve_attack(attacker: int, defender: int, world: "World", bus: "EventBus") -> bool:
    """
    Execute one attack from attacker to defender.
    Returns True if defender died.
    """
    sfx = world.get_component(attacker, StatusEffects)
    if sfx and sfx.is_stunned():
        atk_name = _name(attacker, world)
        bus.publish(MessagePosted(f"{atk_name} is stunned and cannot attack!", "combat"))
        return False

    health = world.get_component(defender, Health)
    if health is None or health.is_dead():
        return True

    damage = calculate_damage(attacker, defender, world)
    actual = health.take_damage(damage)

    atk_name = _name(attacker, world)
    def_name = _name(defender, world)
    bus.publish(MessagePosted(
        f"{atk_name} attacks {def_name} for {actual} damage. "
        f"({health.current}/{health.maximum} HP remaining)",
        "combat",
    ))
    bus.publish(EntityDamaged(attacker=attacker, target=defender, damage=actual))

    if health.is_dead():
        bus.publish(EntityDied(entity=defender, killer=attacker))
        bus.publish(MessagePosted(f"{def_name} has been defeated!", "combat"))
        return True

    return False


def run_combat_round(player: int, enemy: int, world: "World", bus: "EventBus") -> str:
    """
    Execute a full combat round (player turn + enemy counterattack if alive).
    Returns: 'player_won' | 'player_died' | 'ongoing'
    """
    # Player attacks first (based on initiative -- could be reversed if enemy has higher dex)
    player_stats = world.get_component(player, Stats)
    enemy_stats = world.get_component(enemy, Stats)

    player_initiative = (player_stats.dex_modifier if player_stats else 0)
    enemy_initiative = (enemy_stats.dex_modifier if enemy_stats else 0)

    first, second = (player, enemy) if player_initiative >= enemy_initiative else (enemy, player)

    # First attacker
    target_of_first = second
    died = resolve_attack(first, target_of_first, world, bus)
    if died:
        if target_of_first == enemy:
            return "player_won"
        else:
            return "player_died"

    # Second attacker (only if still alive)
    health_second = world.get_component(second, Health)
    if health_second and not health_second.is_dead():
        target_of_second = first
        died = resolve_attack(second, target_of_second, world, bus)
        if died:
            if target_of_second == player:
                return "player_died"
            else:
                return "player_won"

    return "ongoing"


def process_status_effects(entity: int, world: "World", bus: "EventBus") -> None:
    """Tick status effects for an entity at end of their turn."""
    sfx = world.get_component(entity, StatusEffects)
    if not sfx:
        return

    health = world.get_component(entity, Health)
    expired = []

    for effect in sfx.effects:
        name = _name(entity, world)

        if effect.damage_per_turn and health:
            actual = health.take_damage(effect.damage_per_turn)
            bus.publish(MessagePosted(
                f"{name} takes {actual} {effect.name} damage.", "combat"
            ))
            bus.publish(EntityDamaged(attacker=entity, target=entity, damage=actual, damage_type=effect.name))
            if health.is_dead():
                bus.publish(EntityDied(entity=entity, killer=None))

        if effect.heal_per_turn and health:
            actual = health.heal(effect.heal_per_turn)
            if actual > 0:
                bus.publish(EntityHealed(entity=entity, amount=actual))

        effect.remaining_turns -= 1
        if effect.remaining_turns <= 0:
            expired.append(effect.name)

    for name in expired:
        sfx.remove(name)
        bus.publish(StatusEffectExpired(entity=entity, effect=name))
        bus.publish(MessagePosted(f"{_name(entity, world)}'s {name} fades.", "combat"))


def apply_status_effect(entity: int, effect: StatusEffect, world: "World", bus: "EventBus") -> None:
    sfx = world.get_component(entity, StatusEffects)
    if sfx is None:
        sfx = StatusEffects()
        world.add_component(entity, sfx)
    sfx.add(effect)
    bus.publish(StatusEffectApplied(entity=entity, effect=effect.name, duration=effect.remaining_turns))
    bus.publish(MessagePosted(
        f"{_name(entity, world)} is afflicted with {effect.name} for {effect.remaining_turns} turns.",
        "combat",
    ))


def _name(entity: int, world: "World") -> str:
    ident = world.get_component(entity, Identity)
    return ident.name if ident else f"Entity({entity})"
