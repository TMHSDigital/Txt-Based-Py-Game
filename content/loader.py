"""
Content Loader - reads JSON data files and populates the ECS world.

:class:`ContentLoader` is the bridge between the static JSON content
files and the live ECS world. It performs two distinct phases:

1. **Room registration** (:meth:`load_all`): reads every room file,
   creates room entities, and queues exit connections for deferred
   resolution. Exits are deferred because a room in ``overworld.json``
   may reference a room in ``dungeon_01.json`` that has not been loaded
   yet.

2. **Content spawning** (:meth:`spawn_room_contents`): re-reads the
   room files and creates item and enemy entities, placing them in
   their starting rooms.

Cross-zone room references use the ``"zone:room_key"`` format, e.g.
``"overworld:dungeon_01_entrance"`` or ``"dungeon_01:entry_hall"``.
Same-zone references may omit the zone prefix.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World

from content.templates import create_room, create_enemy, create_item
from components.spatial import RoomData, Position
from components.inventory import RoomContents
from systems.movement import connect_rooms


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class ContentLoader:
    """
    Loads all game content from ``data/`` into the ECS world.

    Usage::

        loader = ContentLoader(world)
        loader.load_all()           # create room entities
        loader.spawn_room_contents() # populate with items and enemies
        loader.give_starting_items(player_entity)
    """

    def __init__(self, world: "World") -> None:
        self._world = world
        self._items_data: dict = {}
        self._enemies_data: dict = {}
        self._config: dict = {}
        self._room_registry: dict[str, int] = {}
        self._pending_exits: list[tuple[str, str, str]] = []

    def load_all(self) -> None:
        """
        Parse all data files and create room entities.

        Must be called before :meth:`spawn_room_contents` or any of the
        factory methods. Safe to call on a world that already has rooms
        (e.g. after loading a save) because room entity IDs are
        determined by the world's ``_next_id`` counter.
        """
        self._config = _load_json(os.path.join(DATA_DIR, "config.json"))
        self._items_data = _load_json(os.path.join(DATA_DIR, "items.json"))
        self._enemies_data = _load_json(os.path.join(DATA_DIR, "enemies.json"))

        rooms_dir = os.path.join(DATA_DIR, "rooms")
        for fname in os.listdir(rooms_dir):
            if fname.endswith(".json"):
                zone_file = _load_json(os.path.join(rooms_dir, fname))
                self._load_zone(zone_file)

        self._resolve_exits()

    def _load_zone(self, zone_data: dict) -> None:
        """Create room entities for one zone file and queue their exits."""
        zone = zone_data.get("zone", "unknown")
        rooms = zone_data.get("rooms", {})

        for room_key, room_def in rooms.items():
            entity = create_room(room_key, room_def, zone, self._world)
            registry_key = f"{zone}:{room_key}"
            self._room_registry[registry_key] = entity

            for direction, target_key in room_def.get("exits", {}).items():
                if ":" not in target_key:
                    target_key = f"{zone}:{target_key}"
                self._pending_exits.append((registry_key, direction, target_key))

    def _resolve_exits(self) -> None:
        """
        Wire up all queued exit connections now that all rooms exist.

        Exits that reference an unknown room key are printed as warnings
        and skipped rather than raising an exception.
        """
        for from_key, direction, to_key in self._pending_exits:
            from_id = self._room_registry.get(from_key)
            to_id = self._room_registry.get(to_key)
            if from_id is None or to_id is None:
                print(f"[WARNING] Cannot resolve exit: {from_key} --{direction}--> {to_key}")
                continue
            room_data = self._world.get_component(from_id, RoomData)
            if room_data:
                room_data.add_exit(direction, to_id)

    def spawn_room_contents(self) -> None:
        """
        Create item and enemy entities and place them in their rooms.

        Must be called after :meth:`load_all`. This is separate from
        room creation so that it can be skipped when loading a save
        (the save already contains the live entity state).
        """
        rooms_dir = os.path.join(DATA_DIR, "rooms")
        for fname in os.listdir(rooms_dir):
            if fname.endswith(".json"):
                zone_data = _load_json(os.path.join(rooms_dir, fname))
                zone = zone_data.get("zone", "unknown")
                for room_key, room_def in zone_data.get("rooms", {}).items():
                    registry_key = f"{zone}:{room_key}"
                    room_id = self._room_registry.get(registry_key)
                    if room_id is None:
                        continue

                    for item_key in room_def.get("items", []):
                        item_data = self._items_data.get(item_key)
                        if item_data:
                            item_entity = create_item(item_key, item_data, self._world)
                            self._world.add_component(item_entity, Position(room_id=room_id))
                            contents = self._world.get_component(room_id, RoomContents)
                            if contents:
                                contents.add(item_entity)

                    for enemy_key in room_def.get("enemies", []):
                        enemy_data = self._enemies_data.get(enemy_key)
                        if enemy_data:
                            create_enemy(enemy_key, enemy_data, room_id, self._world)

    def get_starting_room_id(self) -> int | None:
        """Return the entity ID of the player's configured starting room."""
        starting_key = self._config.get("player", {}).get("starting_room", "overworld:town_square")
        return self._room_registry.get(starting_key)

    def get_room_id(self, zone_key: str) -> int | None:
        """Return the entity ID for a room given its ``"zone:room_key"`` address."""
        return self._room_registry.get(zone_key)

    def create_item_by_id(self, item_id: str) -> int | None:
        """
        Create a fresh item entity from its template.

        Returns the new entity ID, or ``None`` if the ``item_id`` is
        not found in ``data/items.json``. Used by the loot system.
        """
        data = self._items_data.get(item_id)
        if data is None:
            return None
        return create_item(item_id, data, self._world)

    def create_enemy_by_id(self, enemy_id: str, room_id: int) -> int | None:
        """
        Create a fresh enemy entity from its template and place it in a room.

        Returns the new entity ID, or ``None`` if ``enemy_id`` is not
        found in ``data/enemies.json``. Used by the spawn system.
        """
        data = self._enemies_data.get(enemy_id)
        if data is None:
            return None
        return create_enemy(enemy_id, data, room_id, self._world)

    def give_starting_items(self, player_entity: int) -> None:
        """
        Give the player the items listed under ``player.starting_items``
        in ``data/config.json``.
        """
        from components.inventory import Inventory
        inv = self._world.get_component(player_entity, Inventory)
        if not inv:
            return
        for item_key in self._config.get("player", {}).get("starting_items", []):
            item_entity = self.create_item_by_id(item_key)
            if item_entity is not None:
                inv.add(item_entity)

    @property
    def config(self) -> dict:
        """The parsed ``data/config.json`` dictionary."""
        return self._config

    @property
    def items_data(self) -> dict:
        """The parsed ``data/items.json`` dictionary."""
        return self._items_data

    @property
    def enemies_data(self) -> dict:
        """The parsed ``data/enemies.json`` dictionary."""
        return self._enemies_data
