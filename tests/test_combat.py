"""Tests for the combat system."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.world import World
from engine.event_bus import EventBus
from components.identity import Identity
from components.combat import Health, Stats, CombatStats, StatusEffects, StatusEffect
from systems.combat import calculate_damage, resolve_attack, run_combat_round, apply_status_effect


def _make_world_with_fighter(name: str, hp: int, atk: int, defense: int) -> tuple[World, EventBus, int]:
    w = World()
    bus = EventBus()
    e = w.create_entity()
    w.add_component(e, Identity(name=name))
    w.add_component(e, Health(current=hp, maximum=hp))
    w.add_component(e, Stats())
    w.add_component(e, CombatStats(base_attack=atk, base_defense=defense))
    w.add_component(e, StatusEffects())
    return w, bus, e


def test_damage_is_at_least_1():
    w = World()
    bus = EventBus()
    attacker = w.create_entity()
    defender = w.create_entity()
    w.add_component(attacker, Identity(name="A"))
    w.add_component(attacker, CombatStats(base_attack=2, base_defense=0))
    w.add_component(attacker, Stats())
    w.add_component(attacker, StatusEffects())
    w.add_component(defender, Identity(name="D"))
    w.add_component(defender, Health(100, 100))
    w.add_component(defender, CombatStats(base_attack=0, base_defense=100))  # massive defense
    w.add_component(defender, Stats())
    w.add_component(defender, StatusEffects())

    dmg = calculate_damage(attacker, defender, w)
    assert dmg >= 1, f"Damage should be at least 1, got {dmg}"


def test_resolve_attack_reduces_health():
    w, bus, attacker = _make_world_with_fighter("Attacker", 100, 20, 0)
    _, _, defender = _make_world_with_fighter("Defender", 50, 5, 0)
    # Ensure they share the same world
    w.add_component(defender, Identity(name="Defender"))
    # We can't easily share worlds, so inline entity creation:
    w2 = World()
    bus2 = EventBus()
    atk = w2.create_entity()
    dfn = w2.create_entity()
    for e, name, hp, atk_val, def_val in [(atk, "Atk", 100, 20, 0), (dfn, "Dfn", 50, 5, 0)]:
        w2.add_component(e, Identity(name=name))
        w2.add_component(e, Health(current=hp, maximum=hp))
        w2.add_component(e, Stats())
        w2.add_component(e, CombatStats(base_attack=atk_val, base_defense=def_val))
        w2.add_component(e, StatusEffects())

    health_before = w2.get_component(dfn, Health).current
    resolve_attack(atk, dfn, w2, bus2)
    health_after = w2.get_component(dfn, Health).current
    assert health_after < health_before


def test_status_effect_applied_and_ticks():
    w = World()
    bus = EventBus()
    entity = w.create_entity()
    w.add_component(entity, Identity(name="Hero"))
    w.add_component(entity, Health(current=100, maximum=100))
    w.add_component(entity, StatusEffects())

    effect = StatusEffect(name="poison", remaining_turns=3, damage_per_turn=5)
    apply_status_effect(entity, effect, w, bus)

    sfx = w.get_component(entity, StatusEffects)
    assert sfx.has("poison")

    from systems.combat import process_status_effects
    process_status_effects(entity, w, bus)
    bus.flush()

    health = w.get_component(entity, Health)
    assert health.current == 95, f"Expected 95 HP after poison tick, got {health.current}"

    sfx2 = w.get_component(entity, StatusEffects)
    remaining = next((e for e in sfx2.effects if e.name == "poison"), None)
    assert remaining is not None
    assert remaining.remaining_turns == 2


def test_combat_round_kills_enemy():
    """A very strong player should win a combat round against a weak enemy."""
    w = World()
    bus = EventBus()

    player = w.create_entity("player")
    enemy = w.create_entity("enemy")

    for e, name, hp, atk, defense in [(player, "Player", 500, 100, 0), (enemy, "Slime", 1, 0, 0)]:
        w.add_component(e, Identity(name=name))
        w.add_component(e, Health(current=hp, maximum=hp))
        w.add_component(e, Stats())
        w.add_component(e, CombatStats(base_attack=atk, base_defense=defense))
        w.add_component(e, StatusEffects())

    result = run_combat_round(player, enemy, w, bus)
    assert result == "player_won", f"Expected player_won, got {result}"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as ex:
            import traceback
            print(f"  FAIL  {t.__name__}: {ex}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
