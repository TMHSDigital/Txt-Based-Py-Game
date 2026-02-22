"""
Abstract renderer interface.

All UI implementations must subclass :class:`Renderer` and implement
its three abstract methods. The game loop calls :meth:`render` once per
frame; individual systems call :meth:`show_message` for immediate
feedback; :meth:`clear` is provided for implementations that manage a
full-screen display.

The game loop and all systems depend on this interface only, never on a
concrete implementation, which is what makes the UI swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.state_machine import StateMachine
    from engine.event_bus import EventBus


class Renderer(ABC):
    """
    Abstract base class for all display backends.

    Concrete implementations are expected to live in a package under
    ``ui/``, such as ``ui/terminal/`` or ``ui/pygame/``. The
    ``game_bootstrap.py`` module selects the implementation.
    """

    @abstractmethod
    def render(self, world: "World", states: "StateMachine", bus: "EventBus") -> None:
        """
        Draw the full current game state to the display.

        Called once per frame by the game loop, before input is read.
        Implementations should inspect ``states.current_name`` to
        determine which view to display.
        """

    @abstractmethod
    def show_message(self, text: str, category: str = "info") -> None:
        """
        Queue or immediately display a single feedback message.

        ``category`` is an arbitrary string that implementations may
        use for colour coding or filtering. Standard values:
        ``"info"``, ``"combat"``, ``"loot"``, ``"quest"``,
        ``"warning"``, ``"error"``, ``"success"``.
        """

    @abstractmethod
    def clear(self) -> None:
        """Clear the display surface."""
