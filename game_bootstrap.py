"""
Game bootstrap - the composition root.

This module is the only place in the codebase where all layers
(engine, components, systems, content, UI) are imported together and
wired up. Game logic modules never import from here; the dependency
arrow always points inward toward the engine.

Three public functions are provided:

:func:`build_new_game`
    Creates a fresh world, loads all content, spawns enemies and items,
    creates the player, and returns a ready-to-run game loop.

:func:`build_loaded_game`
    Loads a saved world snapshot from the default save slot, rewires
    event subscriptions (which are not persisted), and returns a
    ready-to-run game loop. Returns ``None`` if no save file exists.

:func:`run`
    Shows the main menu loop, then hands off to ``build_new_game`` or
    ``build_loaded_game`` based on the player's choice.
"""

from __future__ import annotations

import json
import os
import sys

from engine.world import World
from engine.event_bus import EventBus, MessagePosted
from engine.state_machine import StateMachine
from engine.game_loop import GameLoop
from content.loader import ContentLoader
from content.templates import create_player
from systems.loot import setup_loot_system
from systems.quest import setup_quest_system
from ui.terminal.renderer import TerminalRenderer
from ui.terminal.input_handler import TerminalInputHandler
from components.spatial import Position
from components.quest import QuestLog, Quest, QuestObjective, QuestStatus


def _load_quests(loader: ContentLoader, world: World, player: int) -> None:
    """Load quest definitions and add them to the player's quest log."""
    quests_path = os.path.join(os.path.dirname(__file__), "data", "quests.json")
    if not os.path.exists(quests_path):
        return
    with open(quests_path, "r", encoding="utf-8") as f:
        quests_data = json.load(f)

    log = world.get_component(player, QuestLog)
    if not log:
        return

    for quest_id, qdef in quests_data.items():
        objectives = [
            QuestObjective(
                objective_id=obj["objective_id"],
                description=obj["description"],
                objective_type=obj["objective_type"],
                target_id=obj.get("target_id", ""),
                required_count=obj.get("required_count", 1),
            )
            for obj in qdef.get("objectives", [])
        ]
        quest = Quest(
            quest_id=quest_id,
            title=qdef["title"],
            description=qdef["description"],
            objectives=objectives,
            reward_xp=qdef.get("reward_xp", 0),
            reward_gold=qdef.get("reward_gold", 0),
            reward_items=qdef.get("reward_items", []),
        )
        log.add_quest(quest)


def build_new_game(player_name: str) -> tuple[World, GameLoop, StateMachine]:
    """Create a fresh game world and return it ready to run."""
    world = World()
    bus = EventBus()
    states = StateMachine(bus)
    renderer = TerminalRenderer()
    loop = GameLoop(world, bus, states, renderer, None)  # input_handler set below

    input_handler = TerminalInputHandler(loop, renderer)
    loop._input = input_handler

    # Load all content (rooms, items, enemies)
    loader = ContentLoader(world)
    loader.load_all()
    loader.spawn_room_contents()

    # Create player
    player = create_player(player_name, world, loader.config)
    starting_room = loader.get_starting_room_id()
    if starting_room:
        world.add_component(player, Position(room_id=starting_room))
        # Mark starting room as visited
        from components.spatial import RoomData
        rd = world.get_component(starting_room, RoomData)
        if rd:
            rd.visited = True

    # Give starting items
    loader.give_starting_items(player)

    # Load quest definitions
    _load_quests(loader, world, player)

    # Wire up systems that listen to events
    setup_loot_system(bus, world, loader.create_item_by_id)
    setup_quest_system(bus, world)

    # Message relay: publish events go to renderer log after flush
    def relay_message(event: MessagePosted) -> None:
        renderer.show_message(event.text, event.category)
    bus.subscribe(MessagePosted, relay_message)

    states.transition("exploring")
    return world, loop, states


def build_loaded_game() -> tuple[World, GameLoop, StateMachine] | None:
    """Try to load a saved game. Returns None if no save exists."""
    from saves.save_manager import SaveManager

    world = World()
    bus = EventBus()
    states = StateMachine(bus)
    renderer = TerminalRenderer()
    loop = GameLoop(world, bus, states, renderer, None)
    input_handler = TerminalInputHandler(loop, renderer)
    loop._input = input_handler

    save_mgr = SaveManager(world)
    save_path = os.path.join(os.path.dirname(__file__), "saves", "slot1.json")
    if not save_mgr.load(save_path):
        return None

    # Re-wire event systems (not saved in world snapshot)
    loader = ContentLoader(world)
    loader.load_all()
    setup_loot_system(bus, world, loader.create_item_by_id)
    setup_quest_system(bus, world)

    def relay_message(event: MessagePosted) -> None:
        renderer.show_message(event.text, event.category)
    bus.subscribe(MessagePosted, relay_message)

    states.transition("exploring")
    return world, loop, states


def run() -> None:
    """Top-level entry point. Shows the main menu and starts the game."""
    world = World()
    bus = EventBus()
    states = StateMachine(bus)
    renderer = TerminalRenderer()
    loop = GameLoop(world, bus, states, renderer, None)
    input_handler = TerminalInputHandler(loop, renderer)
    loop._input = input_handler

    # Custom main menu handler that bootstraps the real game
    original_handle = input_handler.handle

    def menu_handle(raw: str, state: str, w, s, b) -> None:
        nonlocal world, loop, states, renderer, input_handler

        if state != "main_menu":
            original_handle(raw, state, w, s, b)
            return

        cmd = raw.strip().lower()
        if cmd in ("n", "new", "new game"):
            renderer.clear()
            name = input("  Enter your character's name: ").strip()
            if not name:
                name = "Hero"
            world2, loop2, states2 = build_new_game(name)
            loop.stop()
            loop2.run()
        elif cmd in ("l", "load", "load game"):
            result = build_loaded_game()
            if result:
                world2, loop2, states2 = result
                loop.stop()
                loop2.run()
            else:
                renderer.show_message("No save file found.", "warning")
        elif cmd in ("q", "quit", "exit"):
            loop.stop()
        else:
            renderer.show_message("Commands: [N]ew Game  [L]oad  [Q]uit", "info")

    input_handler.handle = menu_handle
    states.transition("main_menu")
    loop.run()
