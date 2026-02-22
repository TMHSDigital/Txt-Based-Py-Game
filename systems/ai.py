"""
AI system - determines what action an enemy takes each combat turn.

:func:`get_ai_action` is called by the input handler's combat loop to
ask the enemy what it wants to do. :func:`attempt_flee` is called when
that decision is ``"flee"``.

Behaviour types
---------------
aggressive    Attacks every turn; flees if HP falls to or below
              ``AIBehavior.flee_threshold``.
passive       Takes no action; never retaliates.
coward        Always flees when engaged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.ai import AIBehavior
from components.combat import Health
from components.spatial import Position
from components.identity import Identity
from engine.event_bus import MessagePosted


def get_ai_action(enemy: int, player: int, world: "World", bus: "EventBus") -> str:
    """
    Determine the enemy's action for this combat round.

    Returns one of:
    - ``"attack"`` -- the enemy will strike the player.
    - ``"flee"``   -- the enemy will attempt to escape.
    - ``"skip"``   -- the enemy does nothing (passive behaviour).
    """
    behavior = world.get_component(enemy, AIBehavior)
    if behavior is None:
        return "attack"

    health = world.get_component(enemy, Health)
    behavior_type = behavior.behavior_type

    if behavior_type in ("coward", "aggressive") and health:
        if health.percentage <= behavior.flee_threshold:
            return "flee"

    if behavior_type == "passive":
        return "skip"

    if behavior_type == "coward":
        return "flee"

    return "attack"


def attempt_flee(enemy: int, world: "World", bus: "EventBus") -> bool:
    """
    Execute a flee attempt for an enemy.

    In a text-based game fleeing means the enemy disappears from the
    world entirely. The function always succeeds (no dice roll needed
    for the enemy; only the player's flee attempt is probabilistic).

    Returns ``True`` to indicate the entity was destroyed.
    """
    name = _name(enemy, world)
    bus.publish(MessagePosted(f"The {name} turns and flees!", "combat"))
    world.destroy_entity(enemy)
    return True


def _name(entity: int, world: "World") -> str:
    ident = world.get_component(entity, Identity)
    return ident.name if ident else f"Entity({entity})"
