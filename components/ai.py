"""
AI and loot components for enemy entities.

:class:`AIBehavior` drives how an enemy acts during combat.
:class:`LootTable` defines what items an enemy may drop on death.
:class:`SpawnData` tracks respawn state for enemies that regenerate.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AIBehavior:
    """
    Enemy decision-making configuration.

    ``behavior_type`` selects the decision tree:

    - ``"aggressive"`` -- always attacks; flees if HP falls below
      ``flee_threshold``.
    - ``"passive"`` -- never initiates combat and skips its turn if
      attacked.
    - ``"coward"`` -- immediately flees when aggroed.

    ``flee_threshold`` is the HP fraction (0.0 to 1.0) at which
    aggressive enemies switch to fleeing behaviour.

    ``is_aggroed`` and ``target_entity`` are runtime state updated by
    the AI system during encounters.
    """

    behavior_type: str = "aggressive"
    flee_threshold: float = 0.20
    is_aggroed: bool = False
    target_entity: int | None = None


@dataclass
class LootEntry:
    """A single row in a loot table."""

    item_id: str
    """Content key matching an entry in ``data/items.json``."""
    chance: float
    """Drop probability in ``[0.0, 1.0]``."""
    quantity_min: int = 1
    """Minimum number of this item to drop."""
    quantity_max: int = 1
    """Maximum number of this item to drop."""


@dataclass
class LootTable:
    """
    Drop table attached to an enemy entity.

    On death the loot system rolls each entry in ``entries`` against its
    ``chance`` value and creates an item entity in the room for each
    successful roll. Items in ``guaranteed`` always drop regardless of
    the roll.
    """

    entries: list[LootEntry] = field(default_factory=list)
    guaranteed: list[str] = field(default_factory=list)

    def add_entry(self, item_id: str, chance: float, qty_min: int = 1, qty_max: int = 1) -> None:
        """Append a chance-based loot entry."""
        self.entries.append(LootEntry(item_id, chance, qty_min, qty_max))

    def add_guaranteed(self, item_id: str) -> None:
        """Add an item that always drops from this enemy."""
        self.guaranteed.append(item_id)


@dataclass
class SpawnData:
    """
    Respawn tracking for an enemy.

    ``template_id`` is the key in ``data/enemies.json`` used to
    recreate the enemy when its timer expires.

    ``respawn_turns`` of zero means the enemy does not respawn.
    ``turns_since_death`` is incremented each game turn by the spawn
    system after the enemy dies.
    """

    template_id: str = ""
    respawn_turns: int = 0
    turns_since_death: int = 0
    room_id: int = 0
