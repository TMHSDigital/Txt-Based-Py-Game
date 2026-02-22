"""
Abstract input handler interface.

All UI implementations must subclass :class:`InputHandler` and implement
:meth:`get_input` and :meth:`handle`. The game loop calls ``get_input``
to block and wait for the next command, then passes the raw string to
``handle`` for parsing and dispatch.

Keeping input handling behind an interface means a graphical frontend
can receive events from a mouse or gamepad without changing any game
logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.state_machine import StateMachine
    from engine.event_bus import EventBus


class InputHandler(ABC):
    """
    Abstract base class for all input backends.

    ``get_input`` and ``handle`` are called on every frame by the game
    loop. Implementations must be stateless with respect to the world;
    all side effects should go through the event bus or by directly
    mutating components.
    """

    @abstractmethod
    def get_input(self, state: str) -> str:
        """
        Block until the user provides input, then return it as a string.

        ``state`` is the name of the current game state and may be used
        to customise the prompt or input method.
        """

    @abstractmethod
    def handle(
        self,
        raw_input: str,
        state: str,
        world: "World",
        states: "StateMachine",
        bus: "EventBus",
    ) -> None:
        """
        Parse ``raw_input`` and execute the appropriate game action.

        Implementations should route to per-state command handlers.
        State transitions, world mutations, and user feedback should all
        go through the existing systems and event bus rather than being
        implemented directly here.
        """
