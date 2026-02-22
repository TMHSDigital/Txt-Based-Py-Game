"""
Inventory, equipment, and item data components.

Component overview
------------------
ItemData        Mechanical properties of an item entity: type, slot,
                stat bonuses, and any on-use status effects. Created
                once from JSON template data and never mutated.

Inventory       The list of item entity IDs an entity is currently
                carrying, together with a capacity limit.

Equipment       The currently equipped item in each named slot. When
                an item is equipped it moves out of ``Inventory`` and
                into the corresponding slot here; its stat bonuses are
                applied directly to ``CombatStats``.

RoomContents    The list of item entity IDs lying on the floor of a
                room entity. Items are moved between this and
                ``Inventory`` by the inventory system.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SLOTS = ("head", "chest", "legs", "feet", "main_hand", "off_hand", "ring", "neck")
"""Valid equipment slot names."""


@dataclass
class ItemData:
    """
    Mechanical description of an item.

    This component is attached to every item entity and is the
    authority on what the item does. It is read by the inventory system
    when an item is used or equipped.

    ``consumable`` items are destroyed after use. ``stackable`` items
    are intended to merge in a future stack system. ``on_use_effects``
    defines status effects applied when a consumable is used; each entry
    is a dict with keys ``name``, ``duration``, and optional
    ``damage_per_turn``, ``heal_per_turn``, ``attack_modifier``,
    ``defense_modifier``, ``is_stun``.
    """

    item_id: str = ""
    item_type: str = "misc"
    slot: str = ""
    attack_bonus: int = 0
    defense_bonus: int = 0
    health_restore: int = 0
    max_health_bonus: int = 0
    consumable: bool = False
    stackable: bool = False
    quantity: int = 1
    value: int = 0
    rarity: str = "common"
    on_use_effects: list[dict] = field(default_factory=list)


@dataclass
class Inventory:
    """
    An entity's carried item bag.

    ``items`` is a list of entity IDs. The physical item entities
    remain in the world; the inventory simply records which ones belong
    to this entity.
    """

    items: list[int] = field(default_factory=list)
    capacity: int = 20

    def add(self, item_id: int) -> bool:
        """
        Add an item to the inventory.

        Returns ``True`` on success, ``False`` if the inventory is full.
        """
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item_id)
        return True

    def remove(self, item_id: int) -> bool:
        """
        Remove an item from the inventory.

        Returns ``True`` if the item was present and removed,
        ``False`` otherwise.
        """
        if item_id in self.items:
            self.items.remove(item_id)
            return True
        return False

    def has(self, item_id: int) -> bool:
        """Return ``True`` if the entity is carrying this item."""
        return item_id in self.items

    @property
    def is_full(self) -> bool:
        """Return ``True`` if the inventory is at capacity."""
        return len(self.items) >= self.capacity

    @property
    def count(self) -> int:
        """Current number of items carried."""
        return len(self.items)


@dataclass
class Equipment:
    """
    Items currently worn or wielded, keyed by slot name.

    Slot values are item entity IDs or ``None`` when empty. Valid slot
    names are defined in the :data:`SLOTS` constant.

    When an item is equipped its stat bonuses are applied to
    :class:`~components.combat.CombatStats`; they are removed again on
    unequip.
    """

    slots: dict[str, int | None] = field(
        default_factory=lambda: {s: None for s in SLOTS}
    )

    def equip(self, slot: str, item_id: int) -> int | None:
        """
        Place ``item_id`` in ``slot``.

        Returns the previously equipped item ID, or ``None`` if the
        slot was empty. The caller is responsible for handling the
        displaced item.
        """
        previous = self.slots.get(slot)
        self.slots[slot] = item_id
        return previous

    def unequip(self, slot: str) -> int | None:
        """
        Remove whatever is in ``slot`` and return its entity ID.

        Returns ``None`` if the slot was already empty.
        """
        item_id = self.slots.get(slot)
        if item_id is not None:
            self.slots[slot] = None
        return item_id

    def get(self, slot: str) -> int | None:
        """Return the item entity ID in ``slot``, or ``None``."""
        return self.slots.get(slot)

    def all_equipped(self) -> list[int]:
        """Return a list of entity IDs for all non-empty slots."""
        return [iid for iid in self.slots.values() if iid is not None]

    def total_attack_bonus(self, world) -> int:
        """Sum of ``attack_bonus`` across all equipped items."""
        from components.inventory import ItemData
        total = 0
        for item_id in self.all_equipped():
            data = world.get_component(item_id, ItemData)
            if data:
                total += data.attack_bonus
        return total

    def total_defense_bonus(self, world) -> int:
        """Sum of ``defense_bonus`` across all equipped items."""
        from components.inventory import ItemData
        total = 0
        for item_id in self.all_equipped():
            data = world.get_component(item_id, ItemData)
            if data:
                total += data.defense_bonus
        return total


@dataclass
class RoomContents:
    """
    Items lying on the floor of a room.

    The movement system and loot system place items here when enemies
    drop them or the player drops one. The inventory system removes
    items when the player picks them up.
    """

    items: list[int] = field(default_factory=list)

    def add(self, item_id: int) -> None:
        """Place an item in the room."""
        self.items.append(item_id)

    def has(self, item_id: int) -> bool:
        """Return ``True`` if the item is present in the room."""
        return item_id in self.items

    def remove(self, item_id: int) -> bool:
        """
        Remove an item from the room.

        Returns ``True`` if the item was present, ``False`` otherwise.
        """
        if item_id in self.items:
            self.items.remove(item_id)
            return True
        return False
