"""
Spawn system - enemy respawn timers.

:func:`setup_spawn_system` registers a listener for
:class:`~engine.event_bus.EntityDied` that resets the
``turns_since_death`` counter on the entity's
:class:`~components.ai.SpawnData` component when the entity dies and
has a non-zero ``respawn_turns`` value.

:func:`tick_respawns` should be called each game turn (e.g. registered
as an always-on system hook on the game loop). It increments
``turns_since_death`` for dead enemies and calls ``enemy_factory`` to
recreate them when the timer expires.

``enemy_factory`` has the signature
``(template_id: str, room_id: int, world: World) -> int | None`` and is
typically :meth:`~content.loader.ContentLoader.create_enemy_by_id`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from engine.world import World
    from engine.event_bus import EventBus

from components.ai import SpawnData
from components.identity import Identity
from engine.event_bus import EntityDied


def setup_spawn_system(bus: "EventBus", world: "World", enemy_factory: Callable) -> None:
    """Register death listener to track respawn timers."""
    def on_entity_died(event: EntityDied) -> None:
        spawn_data = world.get_component(event.entity, SpawnData)
        if spawn_data and spawn_data.respawn_turns > 0:
            spawn_data.turns_since_death = 0
    bus.subscribe(EntityDied, on_entity_died)


def tick_respawns(world: "World", bus: "EventBus", enemy_factory: Callable) -> None:
    """
    Called each game turn. Increments respawn timers and spawns
    enemies when their timer expires.
    """
    for entity, (spawn_data,) in world.query(SpawnData):
        if not world.entity_exists(entity):
            continue
        health = None
        from components.combat import Health
        health = world.get_component(entity, Health)
        if health and not health.is_dead():
            continue  # Still alive

        spawn_data.turns_since_death += 1
        if spawn_data.turns_since_death >= spawn_data.respawn_turns:
            new_enemy = enemy_factory(spawn_data.template_id, spawn_data.room_id, world)
            if new_enemy:
                spawn_data.turns_since_death = 0
