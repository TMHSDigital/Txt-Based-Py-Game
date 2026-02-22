"""
Entity factory functions.

Each function here is the canonical way to create a specific type of
entity in the world. Callers pass raw data dicts (from JSON) and receive
a fully initialised entity ID back. All components are added in a single
call so there is no risk of a partially-constructed entity existing in
the world.

These factories are the only place that should instantiate component
objects from raw data; all other code should call the factory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.world import World

from components.identity import Identity
from components.spatial import Position, RoomData
from components.combat import Health, Stats, CombatStats, StatusEffects, Faction
from components.inventory import Inventory, Equipment, ItemData, RoomContents
from components.ai import AIBehavior, LootTable, LootEntry, SpawnData
from components.quest import QuestLog, QuestGiver


def create_player(name: str, world: "World", config: dict) -> int:
    """
    Create the player entity and attach all necessary components.

    Starting values are read from the ``"player"`` section of
    ``data/config.json``. The entity is tagged ``"player"`` and
    ``"actor"``. Position is not set here; the caller is responsible for
    placing the player in the starting room.

    Returns the new entity ID.
    """
    entity = world.create_entity("player", "actor")

    pc = config.get("player", {})
    raw_stats = pc.get("starting_stats", {})
    health_val = pc.get("starting_health", 100)
    inv_cap = pc.get("inventory_capacity", 20)

    world.add_component(entity, Identity(name=name, description="The hero of this tale."))
    world.add_component(entity, Health(current=health_val, maximum=health_val))
    world.add_component(entity, Stats(
        strength=raw_stats.get("strength", 12),
        dexterity=raw_stats.get("dexterity", 10),
        constitution=raw_stats.get("constitution", 12),
        intelligence=raw_stats.get("intelligence", 8),
    ))
    world.add_component(entity, CombatStats(
        base_attack=pc.get("base_attack", 8),
        base_defense=pc.get("base_defense", 3),
    ))
    world.add_component(entity, StatusEffects())
    world.add_component(entity, Inventory(capacity=inv_cap))
    world.add_component(entity, Equipment())
    world.add_component(entity, Faction(name="player", relations={"monsters": 100, "undead": 100, "beasts": 100}))
    world.add_component(entity, QuestLog())
    return entity


def create_item(item_id: str, item_data: dict, world: "World") -> int:
    """
    Create an item entity from a template data dictionary.

    ``item_id`` is the key from ``data/items.json``. ``item_data`` is
    the corresponding value dict. The entity is tagged ``"item"`` but
    is not placed in any room; the caller sets the :class:`Position`
    component and adds the entity to a :class:`RoomContents` list.

    Returns the new entity ID.
    """
    entity = world.create_entity("item")
    world.add_component(entity, Identity(
        name=item_data.get("name", item_id),
        description=item_data.get("description", ""),
    ))
    world.add_component(entity, ItemData(
        item_id=item_id,
        item_type=item_data.get("item_type", "misc"),
        slot=item_data.get("slot", ""),
        attack_bonus=item_data.get("attack_bonus", 0),
        defense_bonus=item_data.get("defense_bonus", 0),
        health_restore=item_data.get("health_restore", 0),
        max_health_bonus=item_data.get("max_health_bonus", 0),
        consumable=item_data.get("consumable", False),
        stackable=item_data.get("stackable", False),
        quantity=item_data.get("quantity", 1),
        value=item_data.get("value", 0),
        rarity=item_data.get("rarity", "common"),
        on_use_effects=item_data.get("on_use_effects", []),
    ))
    return entity


def create_enemy(template_id: str, template: dict, room_id: int, world: "World") -> int:
    """
    Create an enemy entity from a template data dictionary and place it
    in a room.

    ``template_id`` is the key from ``data/enemies.json``. The entity
    is tagged ``"enemy"`` and ``"actor"`` and receives a
    :class:`~components.spatial.Position` component pointing to
    ``room_id``.

    Returns the new entity ID.
    """
    entity = world.create_entity("enemy", "actor")

    raw_stats = template.get("stats", {})
    health_val = template.get("health", 30)

    world.add_component(entity, Identity(
        name=template.get("name", template_id),
        description=template.get("description", ""),
    ))
    world.add_component(entity, Health(current=health_val, maximum=health_val))
    world.add_component(entity, Stats(
        strength=raw_stats.get("strength", 10),
        dexterity=raw_stats.get("dexterity", 10),
        constitution=raw_stats.get("constitution", 10),
        intelligence=raw_stats.get("intelligence", 5),
    ))
    world.add_component(entity, CombatStats(
        base_attack=template.get("base_attack", 5),
        base_defense=template.get("base_defense", 2),
    ))
    world.add_component(entity, StatusEffects())
    world.add_component(entity, Position(room_id=room_id))
    world.add_component(entity, Faction(
        name=template.get("faction", "monsters"),
        relations={"player": 100},
    ))
    world.add_component(entity, AIBehavior(
        behavior_type=template.get("ai", "aggressive"),
        flee_threshold=template.get("flee_threshold", 0.2),
    ))

    loot_data = template.get("loot_table", {})
    loot_table = LootTable()
    for entry in loot_data.get("entries", []):
        loot_table.add_entry(
            entry["item_id"],
            entry["chance"],
            entry.get("quantity_min", 1),
            entry.get("quantity_max", 1),
        )
    for guaranteed in loot_data.get("guaranteed", []):
        loot_table.add_guaranteed(guaranteed)
    world.add_component(entity, loot_table)

    world.add_component(entity, SpawnData(
        template_id=template_id,
        respawn_turns=template.get("respawn_turns", 0),
        room_id=room_id,
    ))

    return entity


def create_room(room_id_key: str, room_data: dict, zone: str, world: "World") -> int:
    """
    Create a room entity.

    Exits are not wired here; that is done by the loader's
    ``_resolve_exits`` method after all rooms in all zones have been
    created.

    Returns the new entity ID.
    """
    entity = world.create_entity("room")
    world.add_component(entity, Identity(
        name=room_data.get("name", room_id_key),
        description=room_data.get("description", ""),
    ))
    world.add_component(entity, RoomData(zone=zone))
    world.add_component(entity, RoomContents())
    return entity
