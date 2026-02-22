"""
Quest system - objective tracking and quest completion.

:func:`setup_quest_system` subscribes to three event types:

- :class:`~engine.event_bus.EntityDied`  -- advances ``"kill"`` objectives.
- :class:`~engine.event_bus.ItemPickedUp` -- advances ``"collect"`` objectives.
- :class:`~engine.event_bus.RoomEntered` -- advances ``"visit"`` objectives.

When all objectives of an active quest are complete,
:func:`_check_completion` transitions the quest to ``COMPLETED`` and
publishes a :class:`~engine.event_bus.QuestCompleted` event.

Template IDs are resolved via :func:`_get_template_id`, which checks
the entity's :class:`~components.inventory.ItemData` (for items),
:class:`~components.ai.SpawnData` (for enemies), and
:class:`~components.identity.Identity` (for rooms) in that order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.quest import QuestLog, QuestStatus
from components.identity import Identity
from engine.event_bus import (
    EntityDied, ItemPickedUp, RoomEntered,
    QuestUpdated, QuestCompleted, MessagePosted,
)


def setup_quest_system(bus: "EventBus", world: "World") -> None:
    """Subscribe to game events to track quest objectives."""

    def on_entity_died(event: EntityDied) -> None:
        killed_template = _get_template_id(event.entity, world)
        if not killed_template:
            return
        for player in world.entities_with_tag("player"):
            log = world.get_component(player, QuestLog)
            if not log:
                continue
            for quest in log.active_quests():
                for obj in quest.objectives:
                    if obj.objective_type == "kill" and obj.target_id == killed_template:
                        obj.increment()
                        bus.publish(QuestUpdated(entity=player, quest_id=quest.quest_id, objective_id=obj.objective_id))
                        bus.publish(MessagePosted(
                            f"[Quest] {quest.title}: {obj.description} ({obj.current_count}/{obj.required_count})",
                            "quest",
                        ))
                        _check_completion(player, quest, world, bus)

    def on_item_picked_up(event: ItemPickedUp) -> None:
        item_template = _get_template_id(event.item, world)
        if not item_template:
            return
        log = world.get_component(event.entity, QuestLog)
        if not log:
            return
        for quest in log.active_quests():
            for obj in quest.objectives:
                if obj.objective_type == "collect" and obj.target_id == item_template:
                    obj.increment()
                    bus.publish(QuestUpdated(entity=event.entity, quest_id=quest.quest_id, objective_id=obj.objective_id))
                    bus.publish(MessagePosted(
                        f"[Quest] {quest.title}: {obj.description} ({obj.current_count}/{obj.required_count})",
                        "quest",
                    ))
                    _check_completion(event.entity, quest, world, bus)

    def on_room_entered(event: RoomEntered) -> None:
        if not world.has_tag(event.entity, "player"):
            return
        room_template = _get_template_id(event.room, world)
        if not room_template:
            return
        log = world.get_component(event.entity, QuestLog)
        if not log:
            return
        for quest in log.active_quests():
            for obj in quest.objectives:
                if obj.objective_type == "visit" and obj.target_id == room_template:
                    if obj.current_count < obj.required_count:
                        obj.increment()
                        bus.publish(QuestUpdated(entity=event.entity, quest_id=quest.quest_id, objective_id=obj.objective_id))
                        _check_completion(event.entity, quest, world, bus)

    bus.subscribe(EntityDied, on_entity_died)
    bus.subscribe(ItemPickedUp, on_item_picked_up)
    bus.subscribe(RoomEntered, on_room_entered)


def _check_completion(player: int, quest, world: "World", bus: "EventBus") -> None:
    if quest.is_complete and quest.status == QuestStatus.ACTIVE:
        quest.status = QuestStatus.COMPLETED
        bus.publish(QuestCompleted(entity=player, quest_id=quest.quest_id))
        bus.publish(MessagePosted(
            f"[Quest Complete] {quest.title}! Rewards: {quest.reward_xp} XP, {quest.reward_gold} gold.",
            "quest",
        ))


def _get_template_id(entity: int, world: "World") -> str | None:
    from components.inventory import ItemData
    from components.ai import SpawnData
    item_data = world.get_component(entity, ItemData)
    if item_data:
        return item_data.item_id
    spawn_data = world.get_component(entity, SpawnData)
    if spawn_data:
        return spawn_data.template_id
    # For rooms, use Identity name as fallback
    ident = world.get_component(entity, Identity)
    if ident and world.has_tag(entity, "room"):
        return ident.name.lower().replace(" ", "_")
    return None
