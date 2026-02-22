"""
Inventory system - item lifecycle management.

All functions accept entity IDs and publish events on the bus rather
than returning rich objects, keeping them decoupled from the UI.

Public API
----------
get_item_in_room_by_name(name_query, room_id, world)
    Case-insensitive partial name search among items on a room's floor.

get_item_in_inventory_by_name(name_query, entity, world)
    Case-insensitive partial name search among items in an entity's bag.

pick_up_item(entity, item_id, world, bus)
    Move an item from the room floor to the entity's inventory.

drop_item(entity, item_id, world, bus)
    Move an item from the entity's inventory to the room floor.
    Auto-unequips the item first if it is currently equipped.

use_item(entity, item_id, world, bus)
    Apply a consumable item's effects and destroy it.

equip_item(entity, item_id, world, bus)
    Move an item from inventory to its designated equipment slot.
    Applies stat bonuses to :class:`~components.combat.CombatStats`.

unequip_item(entity, slot, world, bus)
    Move the item in a slot back to inventory.
    Removes the stat bonuses that were applied on equip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.inventory import Inventory, Equipment, ItemData, RoomContents
from components.combat import Health, CombatStats, StatusEffect, StatusEffects
from components.spatial import Position
from components.identity import Identity
from engine.event_bus import (
    ItemPickedUp, ItemDropped, ItemUsed, ItemEquipped,
    ItemUnequipped, EntityHealed, MessagePosted,
)


def _name(entity: int, world: "World") -> str:
    ident = world.get_component(entity, Identity)
    return ident.name if ident else f"Entity({entity})"


def get_item_in_room_by_name(name_query: str, room_id: int, world: "World") -> int | None:
    """Find an item entity in a room by partial name match (case-insensitive)."""
    contents = world.get_component(room_id, RoomContents)
    if not contents:
        return None
    for item_id in contents.items:
        ident = world.get_component(item_id, Identity)
        if ident and name_query.lower() in ident.name.lower():
            return item_id
    return None


def get_item_in_inventory_by_name(name_query: str, entity: int, world: "World") -> int | None:
    """Find an item in entity's inventory by partial name match."""
    inv = world.get_component(entity, Inventory)
    if not inv:
        return None
    for item_id in inv.items:
        ident = world.get_component(item_id, Identity)
        if ident and name_query.lower() in ident.name.lower():
            return item_id
    return None


def pick_up_item(entity: int, item_id: int, world: "World", bus: "EventBus") -> bool:
    """Move item from room floor to entity's inventory."""
    pos = world.get_component(entity, Position)
    if not pos:
        return False

    contents = world.get_component(pos.room_id, RoomContents)
    if not contents or not contents.has(item_id):
        bus.publish(MessagePosted("That item isn't here.", "warning"))
        return False

    inv = world.get_component(entity, Inventory)
    if not inv:
        return False

    if inv.is_full:
        bus.publish(MessagePosted("Your inventory is full.", "warning"))
        return False

    contents.remove(item_id)
    inv.add(item_id)
    bus.publish(ItemPickedUp(entity=entity, item=item_id, room=pos.room_id))
    item_name = _name(item_id, world)
    bus.publish(MessagePosted(f"You pick up {item_name}.", "info"))
    return True


def drop_item(entity: int, item_id: int, world: "World", bus: "EventBus") -> bool:
    """Move item from entity's inventory to the current room floor."""
    pos = world.get_component(entity, Position)
    if not pos:
        return False

    inv = world.get_component(entity, Inventory)
    if not inv or not inv.has(item_id):
        bus.publish(MessagePosted("You don't have that item.", "warning"))
        return False

    # Unequip first if it's equipped
    eq = world.get_component(entity, Equipment)
    if eq:
        data = world.get_component(item_id, ItemData)
        if data and data.slot and eq.get(data.slot) == item_id:
            unequip_item(entity, data.slot, world, bus)

    inv.remove(item_id)
    contents = world.get_component(pos.room_id, RoomContents)
    if not contents:
        contents = RoomContents()
        world.add_component(pos.room_id, contents)
    contents.add(item_id)

    item_name = _name(item_id, world)
    bus.publish(ItemDropped(entity=entity, item=item_id, room=pos.room_id))
    bus.publish(MessagePosted(f"You drop {item_name}.", "info"))
    return True


def use_item(entity: int, item_id: int, world: "World", bus: "EventBus") -> bool:
    """Use a consumable item. Applies its effects and destroys it."""
    inv = world.get_component(entity, Inventory)
    if not inv or not inv.has(item_id):
        bus.publish(MessagePosted("You don't have that item.", "warning"))
        return False

    data = world.get_component(item_id, ItemData)
    if not data:
        bus.publish(MessagePosted("You can't use that.", "warning"))
        return False

    if not data.consumable:
        bus.publish(MessagePosted("That item isn't consumable. Try 'equip' instead.", "warning"))
        return False

    item_name = _name(item_id, world)
    bus.publish(ItemUsed(entity=entity, item=item_id))

    # Apply healing
    if data.health_restore > 0:
        health = world.get_component(entity, Health)
        if health:
            actual = health.heal(data.health_restore)
            bus.publish(EntityHealed(entity=entity, amount=actual))
            bus.publish(MessagePosted(
                f"You use {item_name} and restore {actual} HP. ({health.current}/{health.maximum})",
                "info",
            ))

    # Apply status effects
    from systems.combat import apply_status_effect
    for effect_data in data.on_use_effects:
        effect = StatusEffect(
            name=effect_data["name"],
            remaining_turns=effect_data.get("duration", 3),
            damage_per_turn=effect_data.get("damage_per_turn", 0),
            heal_per_turn=effect_data.get("heal_per_turn", 0),
            attack_modifier=effect_data.get("attack_modifier", 0),
            defense_modifier=effect_data.get("defense_modifier", 0),
            is_stun=effect_data.get("is_stun", False),
        )
        apply_status_effect(entity, effect, world, bus)

    # Remove from inventory and destroy
    inv.remove(item_id)
    world.destroy_entity(item_id)
    return True


def equip_item(entity: int, item_id: int, world: "World", bus: "EventBus") -> bool:
    """Equip an item from inventory into its designated slot."""
    inv = world.get_component(entity, Inventory)
    if not inv or not inv.has(item_id):
        bus.publish(MessagePosted("You don't have that item.", "warning"))
        return False

    data = world.get_component(item_id, ItemData)
    if not data or not data.slot:
        bus.publish(MessagePosted("That item can't be equipped.", "warning"))
        return False

    eq = world.get_component(entity, Equipment)
    if not eq:
        eq = Equipment()
        world.add_component(entity, eq)

    # Unequip existing item in that slot
    previous_id = eq.get(data.slot)
    if previous_id is not None:
        unequip_item(entity, data.slot, world, bus)

    eq.equip(data.slot, item_id)
    inv.remove(item_id)  # Equipped items leave the "bag" but stay in equipment

    # Apply stat bonuses to CombatStats
    cs = world.get_component(entity, CombatStats)
    if cs:
        cs.attack_bonus += data.attack_bonus
        cs.defense_bonus += data.defense_bonus

    if data.max_health_bonus:
        health = world.get_component(entity, Health)
        if health:
            health.maximum += data.max_health_bonus
            health.current += data.max_health_bonus

    item_name = _name(item_id, world)
    bus.publish(ItemEquipped(entity=entity, item=item_id, slot=data.slot))
    bus.publish(MessagePosted(f"You equip {item_name} in your {data.slot} slot.", "info"))
    return True


def unequip_item(entity: int, slot: str, world: "World", bus: "EventBus") -> bool:
    """Unequip item from slot and return it to inventory."""
    eq = world.get_component(entity, Equipment)
    if not eq:
        return False

    item_id = eq.unequip(slot)
    if item_id is None:
        bus.publish(MessagePosted(f"Nothing equipped in {slot}.", "warning"))
        return False

    inv = world.get_component(entity, Inventory)
    if inv:
        if inv.is_full:
            # Re-equip if no room
            eq.equip(slot, item_id)
            bus.publish(MessagePosted("Inventory full - can't unequip.", "warning"))
            return False
        inv.add(item_id)

    # Remove stat bonuses
    data = world.get_component(item_id, ItemData)
    if data:
        cs = world.get_component(entity, CombatStats)
        if cs:
            cs.attack_bonus -= data.attack_bonus
            cs.defense_bonus -= data.defense_bonus

        if data.max_health_bonus:
            health = world.get_component(entity, Health)
            if health:
                health.maximum -= data.max_health_bonus
                health.current = min(health.current, health.maximum)

    item_name = _name(item_id, world)
    bus.publish(ItemUnequipped(entity=entity, item=item_id, slot=slot))
    bus.publish(MessagePosted(f"You unequip {item_name}.", "info"))
    return True
