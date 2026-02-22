"""
Spatial components.

:class:`Position` tracks which room an entity currently occupies.
:class:`RoomData` is attached to room entities and stores the network
of exits that connect rooms to one another.

Rooms are first-class entities in the ECS world. This means a room can
carry any component, not just ``RoomData``; for example it also carries
:class:`~components.identity.Identity` and
:class:`~components.inventory.RoomContents`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    """
    Records which room entity the owning entity is currently in.

    Systems use this to locate actors, items, and enemies relative to
    one another. Items on the floor also carry a ``Position`` so the
    loot system can place them in the correct room after a kill.
    """

    room_id: int


@dataclass
class RoomData:
    """
    Attached to room entities. Stores exits and zone membership.

    ``exits`` maps a direction string (``"north"``, ``"south"``,
    ``"east"``, ``"west"``, ``"up"``, ``"down"``) to the entity ID of
    the destination room.

    ``zone`` identifies the high-level area the room belongs to, such
    as ``"overworld"`` or ``"dungeon_01"``. Zone names must match the
    ``"zone"`` field in the corresponding JSON room file.

    ``visited`` is set to ``True`` by the movement system the first
    time a player enters the room. It is available for map/fog-of-war
    systems to use in future.
    """

    exits: dict[str, int] = field(default_factory=dict)
    zone: str = "overworld"
    visited: bool = False

    def add_exit(self, direction: str, room_id: int) -> None:
        """Register an exit in the given direction."""
        self.exits[direction] = room_id

    def get_exit(self, direction: str) -> int | None:
        """Return the destination room entity ID, or ``None``."""
        return self.exits.get(direction)

    def remove_exit(self, direction: str) -> None:
        """Remove an exit. No-op if the direction is not present."""
        self.exits.pop(direction, None)
