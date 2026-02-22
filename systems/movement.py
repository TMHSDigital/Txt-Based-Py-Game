"""
Movement system - room transitions and exit wiring.

:func:`move_entity` is the primary entry point. It reads the entity's
:class:`~components.spatial.Position`, looks up the exit in the current
room's :class:`~components.spatial.RoomData`, and updates the position
if the exit is valid. On success it publishes a
:class:`~engine.event_bus.RoomEntered` event so that other systems
(quest tracking, encounter spawning, etc.) can react.

:func:`connect_rooms` is a utility used by the content loader to wire
bidirectional exits between two room entities in one call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.spatial import Position, RoomData
from components.identity import Identity
from engine.event_bus import RoomEntered, MessagePosted

VALID_DIRECTIONS = {"north", "south", "east", "west", "up", "down"}
DIRECTION_OPPOSITES = {
    "north": "south", "south": "north",
    "east": "west", "west": "east",
    "up": "down", "down": "up",
}


def move_entity(entity: int, direction: str, world: "World", bus: "EventBus") -> bool:
    """
    Attempt to move entity in direction. Returns True on success.
    Publishes RoomEntered on success, MessagePosted on failure.
    """
    pos = world.get_component(entity, Position)
    if pos is None:
        return False

    room_data = world.get_component(pos.room_id, RoomData)
    if room_data is None:
        return False

    target_room_id = room_data.get_exit(direction)
    if target_room_id is None:
        bus.publish(MessagePosted(f"You can't go {direction}.", "warning"))
        return False

    # Validate target room exists
    if not world.entity_exists(target_room_id):
        bus.publish(MessagePosted("That passage leads nowhere.", "error"))
        return False

    old_room = pos.room_id
    pos.room_id = target_room_id

    # Mark room as visited
    target_data = world.get_component(target_room_id, RoomData)
    if target_data:
        target_data.visited = True

    bus.publish(RoomEntered(entity=entity, room=target_room_id, direction=direction))
    return True


def connect_rooms(room_a: int, room_b: int, direction: str, world: "World", bidirectional: bool = True) -> None:
    """Connect two room entities. Bidirectional by default."""
    data_a = world.get_component(room_a, RoomData)
    data_b = world.get_component(room_b, RoomData)
    if data_a:
        data_a.add_exit(direction, room_b)
    if bidirectional and data_b:
        opposite = DIRECTION_OPPOSITES.get(direction)
        if opposite:
            data_b.add_exit(opposite, room_a)
