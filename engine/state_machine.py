"""
Game State Machine.

Each :class:`GameState` subclass represents a distinct mode of play.
The active state determines which systems run each frame, how input is
interpreted, and which transitions are legal. Illegal transitions are
rejected without raising an exception; callers should check the return
value of :meth:`StateMachine.transition`.

Defined states and their valid transitions:

    MainMenu   -> Exploring
    Exploring  -> Combat, Inventory, Dialogue, MainMenu, GameOver
    Combat     -> Exploring, GameOver
    Inventory  -> Exploring
    Dialogue   -> Exploring
    GameOver   -> MainMenu
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.event_bus import EventBus


class GameState(ABC):
    """
    Abstract base for all game states.

    Subclasses must declare a ``name`` class attribute and implement
    :meth:`get_valid_transitions`. The optional ``on_enter`` and
    ``on_exit`` hooks are called by the :class:`StateMachine` during
    transitions.
    """

    name: str = "base"

    def on_enter(self) -> None:
        """Called by the state machine when this state becomes active."""

    def on_exit(self) -> None:
        """Called by the state machine just before leaving this state."""

    @abstractmethod
    def get_valid_transitions(self) -> list[str]:
        """Return the list of state names this state may transition to."""


class MainMenuState(GameState):
    """The title / main menu screen shown at startup and after game over."""

    name = "main_menu"

    def get_valid_transitions(self) -> list[str]:
        return ["exploring"]


class ExploringState(GameState):
    """The default play state: moving between rooms, picking up items."""

    name = "exploring"

    def get_valid_transitions(self) -> list[str]:
        return ["combat", "inventory", "dialogue", "main_menu", "game_over"]


class CombatState(GameState):
    """Active combat against a single enemy."""

    name = "combat"

    def get_valid_transitions(self) -> list[str]:
        return ["exploring", "game_over"]


class InventoryState(GameState):
    """The inventory management screen."""

    name = "inventory"

    def get_valid_transitions(self) -> list[str]:
        return ["exploring"]


class DialogueState(GameState):
    """Conversation with an NPC."""

    name = "dialogue"

    def get_valid_transitions(self) -> list[str]:
        return ["exploring"]


class GameOverState(GameState):
    """Displayed when the player dies."""

    name = "game_over"

    def get_valid_transitions(self) -> list[str]:
        return ["main_menu"]


class StateMachine:
    """
    Manages the active :class:`GameState` and validates transitions.

    The machine starts with no active state. The first call to
    :meth:`transition` should target ``"main_menu"`` or
    ``"exploring"``. All six default states are registered
    automatically; additional custom states can be added via
    :meth:`register`.

    Transitions fire a :class:`~engine.event_bus.GameStateChanged`
    event immediately (not deferred) so that the renderer and input
    handler always see the correct state on the next frame.
    """

    def __init__(self, event_bus: "EventBus") -> None:
        self._bus = event_bus
        self._states: dict[str, GameState] = {}
        self._current: GameState | None = None
        self._register_defaults()

    def _register_defaults(self) -> None:
        for state in [
            MainMenuState(),
            ExploringState(),
            CombatState(),
            InventoryState(),
            DialogueState(),
            GameOverState(),
        ]:
            self._states[state.name] = state

    def register(self, state: GameState) -> None:
        """Add or replace a state in the machine's state table."""
        self._states[state.name] = state

    @property
    def current(self) -> GameState | None:
        """The currently active :class:`GameState`, or ``None`` before the first transition."""
        return self._current

    @property
    def current_name(self) -> str:
        """The name of the active state, or an empty string before the first transition."""
        return self._current.name if self._current else ""

    def transition(self, target_name: str) -> bool:
        """
        Attempt to move to the named state.

        Returns ``True`` on success. Returns ``False`` if the transition
        is not listed as valid by the current state's
        :meth:`GameState.get_valid_transitions`. Raises ``ValueError``
        if ``target_name`` is not a registered state name.

        On success: calls ``on_exit`` on the current state, updates
        ``self._current``, calls ``on_enter`` on the new state, and
        publishes a :class:`~engine.event_bus.GameStateChanged` event
        immediately.
        """
        from engine.event_bus import GameStateChanged

        if target_name not in self._states:
            raise ValueError(f"Unknown state: {target_name!r}")

        if self._current is not None:
            if target_name not in self._current.get_valid_transitions():
                return False
            previous = self._current.name
            self._current.on_exit()
        else:
            previous = ""

        self._current = self._states[target_name]
        self._current.on_enter()
        self._bus.publish_immediate(GameStateChanged(previous=previous, current=target_name))
        return True

    def is_in(self, state_name: str) -> bool:
        """Return ``True`` if the machine is currently in the named state."""
        return self.current_name == state_name
