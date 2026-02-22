"""
Game Loop - drives the frame cycle: render -> input -> systems -> flush.

Each iteration of the loop:
  1. Renders the current state via the :class:`~ui.renderer.Renderer`.
  2. Reads player input via the :class:`~ui.input_handler.InputHandler`.
  3. Dispatches the input to the current state's command handler.
  4. Runs all system hooks registered for the active state, then all
     always-on hooks.
  5. Flushes queued events on the :class:`~engine.event_bus.EventBus`.

System functions can be registered with :meth:`GameLoop.register_system`
and are called with ``(world, bus)`` each frame. Systems registered
without a state argument run every frame regardless of state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from engine.event_bus import EventBus
    from engine.state_machine import StateMachine
    from engine.world import World
    from ui.renderer import Renderer
    from ui.input_handler import InputHandler


class GameLoop:
    """
    Orchestrates the main loop.

    The loop runs until :meth:`stop` is called, which sets an internal
    flag that causes the ``while`` loop to exit cleanly after the
    current iteration completes.
    """

    def __init__(
        self,
        world: "World",
        event_bus: "EventBus",
        state_machine: "StateMachine",
        renderer: "Renderer",
        input_handler: "InputHandler",
    ) -> None:
        self._world = world
        self._bus = event_bus
        self._states = state_machine
        self._renderer = renderer
        self._input = input_handler
        self._running = False
        # {state_name: [system_fn(world, bus)]}
        self._update_hooks: dict[str, list[Callable]] = {}
        # system functions that run in every state
        self._always_hooks: list[Callable] = []

    def register_system(self, system_fn: Callable, *states: str) -> None:
        """
        Register a system update function.

        ``system_fn`` must accept ``(world, bus)`` as its two arguments.
        If ``states`` is empty, the function runs every frame regardless
        of the active state. Otherwise it runs only when the active
        state matches one of the provided state names.
        """
        if not states:
            self._always_hooks.append(system_fn)
        else:
            for state in states:
                self._update_hooks.setdefault(state, []).append(system_fn)

    def run(self) -> None:
        """
        Enter the game loop and block until :meth:`stop` is called.

        Should only be called once per loop instance. To restart or
        rebuild the game, construct a new :class:`GameLoop`.
        """
        self._running = True
        while self._running:
            state = self._states.current_name

            self._renderer.render(self._world, self._states, self._bus)

            raw_input = self._input.get_input(state)
            self._input.handle(raw_input, state, self._world, self._states, self._bus)

            for hook in self._always_hooks:
                hook(self._world, self._bus)

            for hook in self._update_hooks.get(state, []):
                hook(self._world, self._bus)

            self._bus.flush()

    def stop(self) -> None:
        """Signal the loop to exit after the current iteration completes."""
        self._running = False
