"""Tests for the inventory system."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.world import World
from engine.event_bus import EventBus
from components.identity import Identity
from components.spatial import Position
from components.combat import Health, CombatStats, StatusEffects
from components.inventory import Inventory, Equipment, ItemData, RoomContents
from systems.inventory import pick_up_item, drop_item, use_item, equip_item, unequip_item


def _setup():
    """Create a minimal world with a player and a room."""
    w = World()
    bus = EventBus()

    room = w.create_entity("room")
    w.add_component(room, RoomContents())

    player = w.create_entity("player")
    w.add_component(player, Identity(name="Hero"))
    w.add_component(player, Position(room_id=room))
    w.add_component(player, Inventory(capacity=10))
    w.add_component(player, Equipment())
    w.add_component(player, Health(current=80, maximum=100))
    w.add_component(player, CombatStats(base_attack=5, base_defense=2))
    w.add_component(player, StatusEffects())

    return w, bus, player, room


def _make_item(w, room, item_id, name, **kwargs):
    item = w.create_entity("item")
    w.add_component(item, Identity(name=name))
    w.add_component(item, Position(room_id=room))
    w.add_component(item, ItemData(
        item_id=item_id,
        item_type=kwargs.get("item_type", "misc"),
        slot=kwargs.get("slot", ""),
        attack_bonus=kwargs.get("attack_bonus", 0),
        defense_bonus=kwargs.get("defense_bonus", 0),
        health_restore=kwargs.get("health_restore", 0),
        consumable=kwargs.get("consumable", False),
    ))
    contents = w.get_component(room, RoomContents)
    contents.add(item)
    return item


def test_pick_up_item():
    w, bus, player, room = _setup()
    item = _make_item(w, room, "sword", "Sword")

    result = pick_up_item(player, item, w, bus)
    assert result is True

    inv = w.get_component(player, Inventory)
    assert inv.has(item)

    contents = w.get_component(room, RoomContents)
    assert item not in contents.items


def test_pick_up_respects_capacity():
    w, bus, player, room = _setup()
    inv = w.get_component(player, Inventory)
    inv.capacity = 1

    item1 = _make_item(w, room, "sword1", "Sword 1")
    item2 = _make_item(w, room, "sword2", "Sword 2")

    pick_up_item(player, item1, w, bus)
    result = pick_up_item(player, item2, w, bus)
    assert result is False
    assert inv.count == 1


def test_drop_item():
    w, bus, player, room = _setup()
    item = _make_item(w, room, "dagger", "Dagger")
    pick_up_item(player, item, w, bus)

    result = drop_item(player, item, w, bus)
    assert result is True

    inv = w.get_component(player, Inventory)
    assert not inv.has(item)

    contents = w.get_component(room, RoomContents)
    assert item in contents.items


def test_use_consumable():
    w, bus, player, room = _setup()
    item = _make_item(w, room, "potion", "Health Potion",
                      item_type="consumable", health_restore=30, consumable=True)
    pick_up_item(player, item, w, bus)

    health = w.get_component(player, Health)
    assert health.current == 80

    result = use_item(player, item, w, bus)
    assert result is True
    assert health.current == 100  # Capped at max

    # Item should be consumed
    assert not w.entity_exists(item)
    inv = w.get_component(player, Inventory)
    assert not inv.has(item)


def test_equip_and_unequip():
    w, bus, player, room = _setup()
    item = _make_item(w, room, "sword", "Long Sword",
                      item_type="weapon", slot="main_hand", attack_bonus=10)
    pick_up_item(player, item, w, bus)

    cs_before = w.get_component(player, CombatStats).total_attack
    equip_item(player, item, w, bus)

    eq = w.get_component(player, Equipment)
    assert eq.get("main_hand") == item
    cs_after = w.get_component(player, CombatStats).total_attack
    assert cs_after == cs_before + 10

    unequip_item(player, "main_hand", w, bus)
    assert eq.get("main_hand") is None
    cs_unequipped = w.get_component(player, CombatStats).total_attack
    assert cs_unequipped == cs_before


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
