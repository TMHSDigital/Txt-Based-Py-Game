"""
Combat components.

This module defines the data components used by the combat, status
effect, and AI systems. None of these classes contain game logic; all
calculations live in ``systems/combat.py``.

Component overview
------------------
Health          Current and maximum HP. Provides helper methods for
                damage and healing that clamp to [0, maximum].

Stats           Core RPG attributes (STR, DEX, CON, INT) and their
                D&D-style modifiers ((attr - 10) // 2).

CombatStats     Derived combat numbers: base attack, base defense, and
                flat bonuses accumulated from equipped items.

StatusEffect    A single timed effect active on an entity.

StatusEffects   The collection of all active effects on an entity.

Faction         Group membership and hostility relations used by the AI
                system to decide whether to engage.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Health:
    """Hit points for any entity that can take damage or be healed."""

    current: int
    maximum: int

    def is_dead(self) -> bool:
        """Return ``True`` if current HP is zero or below."""
        return self.current <= 0

    def take_damage(self, amount: int) -> int:
        """
        Reduce HP by ``amount``, clamped to zero.

        Returns the actual damage applied (may be less than ``amount``
        if the entity had fewer HP remaining).
        """
        actual = min(amount, self.current)
        self.current = max(0, self.current - amount)
        return actual

    def heal(self, amount: int) -> int:
        """
        Increase HP by ``amount``, clamped to ``maximum``.

        Returns the actual amount healed (may be less than ``amount``
        if the entity was already near full HP).
        """
        before = self.current
        self.current = min(self.maximum, self.current + amount)
        return self.current - before

    @property
    def percentage(self) -> float:
        """Current HP as a fraction of maximum, in ``[0.0, 1.0]``."""
        return self.current / self.maximum if self.maximum > 0 else 0.0


@dataclass
class Stats:
    """
    Core RPG attributes.

    Modifier properties follow the standard formula ``(attr - 10) // 2``,
    which yields 0 at 10, +1 at 12, -1 at 8, and so on.
    """

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10

    @property
    def str_modifier(self) -> int:
        """Strength modifier applied to melee attack rolls."""
        return (self.strength - 10) // 2

    @property
    def dex_modifier(self) -> int:
        """Dexterity modifier used for initiative order."""
        return (self.dexterity - 10) // 2

    @property
    def con_modifier(self) -> int:
        """Constitution modifier. Reserved for future HP scaling."""
        return (self.constitution - 10) // 2

    @property
    def int_modifier(self) -> int:
        """Intelligence modifier. Reserved for future spell systems."""
        return (self.intelligence - 10) // 2


@dataclass
class CombatStats:
    """
    Derived combat values.

    ``base_attack`` and ``base_defense`` come from the entity's template.
    ``attack_bonus`` and ``defense_bonus`` are the running total of
    equipment contributions; the inventory system increments and
    decrements them as items are equipped and unequipped.
    """

    base_attack: int = 5
    base_defense: int = 2
    base_initiative: int = 10
    attack_bonus: int = 0
    defense_bonus: int = 0

    @property
    def total_attack(self) -> int:
        """Base attack plus all active equipment bonuses."""
        return self.base_attack + self.attack_bonus

    @property
    def total_defense(self) -> int:
        """Base defense plus all active equipment bonuses."""
        return self.base_defense + self.defense_bonus


@dataclass
class StatusEffect:
    """
    A single timed effect active on an entity.

    Fields control what happens each turn the effect is active.
    Multiple fields may be non-zero simultaneously (e.g. a burning
    effect could deal damage and reduce defense).
    """

    name: str
    remaining_turns: int
    damage_per_turn: int = 0
    heal_per_turn: int = 0
    attack_modifier: int = 0
    defense_modifier: int = 0
    is_stun: bool = False


@dataclass
class StatusEffects:
    """
    Collection of :class:`StatusEffect` instances active on an entity.

    Adding a new effect with the same name as an existing one replaces
    the old one rather than stacking, so refreshing a poison on an
    already-poisoned enemy resets its duration.
    """

    effects: list[StatusEffect] = field(default_factory=list)

    def add(self, effect: StatusEffect) -> None:
        """Add an effect, replacing any existing effect with the same name."""
        self.effects = [e for e in self.effects if e.name != effect.name]
        self.effects.append(effect)

    def remove(self, name: str) -> None:
        """Remove the effect with the given name. No-op if absent."""
        self.effects = [e for e in self.effects if e.name != name]

    def has(self, name: str) -> bool:
        """Return ``True`` if an effect with this name is active."""
        return any(e.name == name for e in self.effects)

    def is_stunned(self) -> bool:
        """Return ``True`` if any active effect sets ``is_stun = True``."""
        return any(e.is_stun for e in self.effects)

    def attack_modifier(self) -> int:
        """Sum of ``attack_modifier`` across all active effects."""
        return sum(e.attack_modifier for e in self.effects)

    def defense_modifier(self) -> int:
        """Sum of ``defense_modifier`` across all active effects."""
        return sum(e.defense_modifier for e in self.effects)


@dataclass
class Faction:
    """
    Group membership and hostility relationships.

    ``relations`` maps faction name strings to an integer attitude:
    positive values indicate hostility, negative values indicate
    friendliness. Zero or absent means neutral.

    Example: the player faction sets ``{"monsters": 100, "undead": 100}``
    so that goblin and skeleton enemies (whose factions set
    ``{"player": 100}``) attack on sight.
    """

    name: str = "neutral"
    relations: dict[str, int] = field(default_factory=dict)

    def is_hostile_to(self, other_faction: str) -> bool:
        """Return ``True`` if this faction's attitude toward ``other_faction`` is positive."""
        return self.relations.get(other_faction, 0) > 0
