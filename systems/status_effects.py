"""
Status effects system - per-turn effect processing.

Thin wrappers around :func:`systems.combat.process_status_effects`.
:func:`tick_status_effects` processes one entity (called from the combat
loop after each combatant's turn). :func:`tick_all_status_effects` is
available for systems that want to advance all effects globally (e.g.
a world-tick hook registered on the game loop).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.combat import StatusEffects
from systems.combat import process_status_effects


def tick_status_effects(entity: int, world: "World", bus: "EventBus") -> None:
    """Process all status effects for an entity (called once per their turn)."""
    process_status_effects(entity, world, bus)


def tick_all_status_effects(world: "World", bus: "EventBus") -> None:
    """Tick status effects for all entities that have them."""
    for entity, (sfx,) in world.query(StatusEffects):
        if world.entity_exists(entity):
            process_status_effects(entity, world, bus)
