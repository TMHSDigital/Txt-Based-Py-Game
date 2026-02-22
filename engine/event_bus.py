"""
Event Bus - typed pub/sub system that decouples game systems.

Systems publish typed event dataclasses; other systems subscribe to
them by event type. Events queued via :meth:`EventBus.publish` are held
until :meth:`EventBus.flush` is called at the end of each frame, which
prevents cascading mid-update mutations. Events that must take effect
immediately (e.g. UI feedback during input handling) use
:meth:`EventBus.publish_immediate` instead.

All game event types are defined as frozen-style dataclasses at the
bottom of this module. Using concrete types rather than string tags
makes subscriptions type-safe and refactor-friendly.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Type, TypeVar

T = TypeVar("T")


class EventBus:
    """
    Central message broker.

    Subscribers register a callable against a specific event type.
    Publishers post event instances. The bus delivers each event to all
    registered handlers for that type, either deferred (end of frame)
    or immediately.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable]] = defaultdict(list)
        self._queue: list[Any] = []

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """
        Register ``handler`` to be called whenever an event of
        ``event_type`` is dispatched.

        The same handler may be registered multiple times; each
        registration results in an additional call per event.
        """
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """
        Remove the first matching registration of ``handler`` for
        ``event_type``.

        Silently does nothing if the handler is not registered.
        """
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Any) -> None:
        """
        Enqueue an event for deferred dispatch.

        The event will be delivered to subscribers when :meth:`flush`
        is next called. Use this for normal in-game events so that
        handlers cannot mutate world state mid-iteration.
        """
        self._queue.append(event)

    def publish_immediate(self, event: Any) -> None:
        """
        Dispatch an event synchronously to all current subscribers.

        Use this only when the caller needs the handler side-effects to
        complete before continuing, e.g. immediate UI feedback during
        input handling or state machine transitions.
        """
        for handler in list(self._subscribers.get(type(event), [])):
            handler(event)

    def flush(self) -> None:
        """
        Deliver all queued events to their subscribers, then clear the
        queue.

        Handlers may themselves publish new events; those are collected
        into a new batch and delivered in subsequent iterations until the
        queue is empty. Call this once at the end of each game loop
        frame.
        """
        while self._queue:
            batch = self._queue[:]
            self._queue.clear()
            for event in batch:
                for handler in list(self._subscribers.get(type(event), [])):
                    handler(event)


# ---------------------------------------------------------------------------
# Game event types
#
# Each dataclass below represents a discrete thing that happened in the
# game world. Fields use entity IDs (integers) rather than object
# references to avoid coupling systems to each other's component types.
# ---------------------------------------------------------------------------

@dataclass
class EntityDamaged:
    """Published after any entity takes damage from an attack or effect."""
    attacker: int
    target: int
    damage: int
    damage_type: str = "physical"


@dataclass
class EntityDied:
    """Published when an entity's Health reaches zero."""
    entity: int
    killer: int | None = None


@dataclass
class EntityHealed:
    """Published when an entity gains HP from any source."""
    entity: int
    amount: int


@dataclass
class RoomEntered:
    """Published when an entity moves into a new room."""
    entity: int
    room: int
    direction: str = ""


@dataclass
class ItemPickedUp:
    """Published when an entity picks an item up from the room floor."""
    entity: int
    item: int
    room: int


@dataclass
class ItemDropped:
    """Published when an entity drops an item onto the room floor."""
    entity: int
    item: int
    room: int


@dataclass
class ItemUsed:
    """Published at the start of item use, before effects are applied."""
    entity: int
    item: int


@dataclass
class ItemEquipped:
    """Published when an item is moved from inventory into an equipment slot."""
    entity: int
    item: int
    slot: str


@dataclass
class ItemUnequipped:
    """Published when an item is removed from an equipment slot."""
    entity: int
    item: int
    slot: str


@dataclass
class CombatStarted:
    """Published when combat begins between the player and an enemy."""
    player: int
    enemy: int


@dataclass
class CombatEnded:
    """Published when a combat encounter concludes."""
    player: int
    enemy: int | None
    victory: bool


@dataclass
class QuestUpdated:
    """Published when a quest objective makes progress."""
    entity: int
    quest_id: str
    objective_id: str


@dataclass
class QuestCompleted:
    """Published when all objectives in a quest are satisfied."""
    entity: int
    quest_id: str


@dataclass
class StatusEffectApplied:
    """Published when a status effect is added to an entity."""
    entity: int
    effect: str
    duration: int


@dataclass
class StatusEffectExpired:
    """Published when a status effect runs out of turns."""
    entity: int
    effect: str


@dataclass
class GameStateChanged:
    """Published immediately whenever the state machine transitions."""
    previous: str
    current: str


@dataclass
class MessagePosted:
    """
    A human-readable message to display in the UI log.

    ``category`` controls the colour used by the terminal renderer:
    ``"info"``, ``"combat"``, ``"loot"``, ``"quest"``, ``"warning"``,
    ``"error"``, ``"success"``.
    """
    text: str
    category: str = "info"
