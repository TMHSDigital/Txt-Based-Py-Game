"""
Loot system - drop table resolution on entity death.

:func:`setup_loot_system` registers a listener on the event bus for
:class:`~engine.event_bus.EntityDied`. When an entity with a
:class:`~components.ai.LootTable` component dies, the system rolls
each entry and creates item entities in the room where the entity fell.

``item_factory`` is a callable with the signature
``(item_id: str, world: World) -> int | None`` and is typically
:meth:`~content.loader.ContentLoader.create_item_by_id`. It is passed
in at setup time rather than imported here to avoid a circular import
between the content and systems layers.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.ai import LootTable
from components.spatial import Position
from components.inventory import RoomContents
from engine.event_bus import EntityDied, MessagePosted


def setup_loot_system(bus: "EventBus", world: "World", item_factory) -> None:
    """Wire up the loot system to the event bus."""
    def on_entity_died(event: EntityDied) -> None:
        _drop_loot(event.entity, world, bus, item_factory)
    bus.subscribe(EntityDied, on_entity_died)


def _drop_loot(entity: int, world: "World", bus: "EventBus", item_factory) -> None:
    """Roll the entity's loot table and spawn items in its current room."""
    loot_table = world.get_component(entity, LootTable)
    if not loot_table:
        return

    pos = world.get_component(entity, Position)
    if not pos:
        return

    dropped: list[str] = []

    # Guaranteed drops
    for item_id_key in loot_table.guaranteed:
        item_entity = item_factory(item_id_key, world)
        if item_entity is not None:
            _place_in_room(item_entity, pos.room_id, world)
            dropped.append(item_id_key)

    # Chance-based drops
    for entry in loot_table.entries:
        roll = random.random()
        if roll <= entry.chance:
            qty = random.randint(entry.quantity_min, entry.quantity_max)
            for _ in range(qty):
                item_entity = item_factory(entry.item_id, world)
                if item_entity is not None:
                    _place_in_room(item_entity, pos.room_id, world)
            dropped.append(entry.item_id)

    if dropped:
        bus.publish(MessagePosted(
            f"Items dropped: {', '.join(dropped)}",
            "loot",
        ))


def _place_in_room(item_entity: int, room_id: int, world: "World") -> None:
    from components.spatial import Position as Pos
    contents = world.get_component(room_id, RoomContents)
    if not contents:
        contents = RoomContents()
        world.add_component(room_id, contents)
    contents.add(item_entity)
    world.add_component(item_entity, Pos(room_id=room_id))
