"""
Terminal renderer - ANSI-coloured stdout implementation of the renderer
interface.

Renders each game state by printing structured text to the terminal.
ANSI escape codes provide colour and bold formatting; terminals that do
not support them will display the raw escape sequences, so Windows users
may need to enable virtual terminal processing or upgrade to Windows
Terminal.

The :class:`Color` class centralises all escape sequences. Swapping
to the ``rich`` library in future would only require replacing the
format strings inside this module, with no changes to game logic.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.state_machine import StateMachine
    from engine.event_bus import EventBus

from ui.renderer import Renderer
from components.identity import Identity
from components.combat import Health, CombatStats, StatusEffects
from components.spatial import Position, RoomData
from components.inventory import Inventory, Equipment, ItemData, RoomContents
from components.quest import QuestLog, QuestStatus


class Color:
    """ANSI escape code constants. All rendering uses these names rather than raw codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    DIM = "\033[2m"

CATEGORY_COLORS = {
    "info": Color.WHITE,
    "combat": Color.RED,
    "loot": Color.YELLOW,
    "quest": Color.CYAN,
    "warning": Color.YELLOW,
    "error": Color.RED,
    "success": Color.GREEN,
}

RARITY_COLORS = {
    "common": Color.WHITE,
    "uncommon": Color.GREEN,
    "rare": Color.BLUE,
    "epic": Color.MAGENTA,
    "legendary": Color.YELLOW,
}

HP_BAR_WIDTH = 20


def _hp_bar(current: int, maximum: int) -> str:
    if maximum <= 0:
        return "[----------]"
    filled = int(HP_BAR_WIDTH * current / maximum)
    empty = HP_BAR_WIDTH - filled
    pct = current / maximum
    if pct > 0.6:
        color = Color.GREEN
    elif pct > 0.3:
        color = Color.YELLOW
    else:
        color = Color.RED
    bar = f"{color}{'█' * filled}{'░' * empty}{Color.RESET}"
    return f"[{bar}] {current}/{maximum}"


class TerminalRenderer(Renderer):
    """
    Concrete renderer that writes to stdout.

    Each frame, the terminal is cleared and the appropriate view for the
    active game state is printed. A scrolling message log at the bottom
    of the screen shows the most recent game feedback (combat results,
    loot drops, quest updates, etc.).
    """

    def __init__(self) -> None:
        self._message_log: list[tuple[str, str]] = []
        self._max_log = 8

    def clear(self) -> None:
        """Clear the terminal screen using the platform-appropriate command."""
        os.system("cls" if os.name == "nt" else "clear")

    def show_message(self, text: str, category: str = "info") -> None:
        """
        Append a message to the on-screen log.

        Older messages are evicted once the log exceeds ``_max_log``
        entries. The log is rendered at the bottom of each frame.
        """
        self._message_log.append((text, category))
        if len(self._message_log) > self._max_log:
            self._message_log.pop(0)

    def render(self, world: "World", states: "StateMachine", bus: "EventBus") -> None:
        from engine.event_bus import MessagePosted
        # Collect any pending MessagePosted events into the log
        # (They're flushed after render, so we peek at them here via a direct subscription)

        state = states.current_name
        self.clear()

        self._print_header(state)

        if state == "exploring":
            self._render_exploring(world, states)
        elif state == "combat":
            self._render_combat(world, states)
        elif state == "inventory":
            self._render_inventory(world, states)
        elif state == "main_menu":
            self._render_main_menu()
        elif state == "game_over":
            self._render_game_over()
        elif state == "dialogue":
            self._render_dialogue(world, states)

        self._render_message_log()

    def _print_header(self, state: str) -> None:
        label = state.upper().replace("_", " ")
        width = 60
        print(f"{Color.BOLD}{Color.CYAN}{'═' * width}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}  DUNGEON CRAWLER  {Color.GRAY}[{label}]{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}{'═' * width}{Color.RESET}")

    def _get_player(self, world: "World") -> int | None:
        players = world.entities_with_tag("player")
        return players[0] if players else None

    def _render_exploring(self, world: "World", states) -> None:
        player = self._get_player(world)
        if not player:
            return

        self._render_player_stats(player, world)
        print()

        pos = world.get_component(player, Position)
        if not pos:
            return

        room_id = pos.room_id
        room_ident = world.get_component(room_id, Identity)
        room_data = world.get_component(room_id, RoomData)

        if room_ident:
            print(f"{Color.BOLD}{Color.YELLOW}  {room_ident.name}{Color.RESET}")
            print(f"{Color.DIM}  {room_ident.description}{Color.RESET}")
        print()

        # Exits
        if room_data and room_data.exits:
            exits_str = ", ".join(room_data.exits.keys())
            print(f"  {Color.GRAY}Exits:{Color.RESET} {exits_str}")

        # Items on floor
        contents = world.get_component(room_id, RoomContents)
        if contents and contents.items:
            print(f"\n  {Color.YELLOW}Items here:{Color.RESET}")
            for item_id in contents.items:
                ident = world.get_component(item_id, Identity)
                data = world.get_component(item_id, ItemData)
                if ident:
                    rarity_color = RARITY_COLORS.get(data.rarity if data else "common", Color.WHITE)
                    print(f"    {rarity_color}• {ident.name}{Color.RESET}"
                          + (f" - {ident.description}" if ident.description else ""))

        # Enemies
        enemies = [e for e in world.entities_with_tag("enemy")
                   if (world.get_component(e, Position) or type('', (), {'room_id': -1})()).room_id == room_id]
        # Better enemy query:
        enemies_in_room = []
        for e in world.entities_with_tag("enemy"):
            epos = world.get_component(e, Position)
            if epos and epos.room_id == room_id:
                ehealth = world.get_component(e, Health)
                if ehealth and not ehealth.is_dead():
                    enemies_in_room.append(e)

        if enemies_in_room:
            print(f"\n  {Color.RED}Enemies:{Color.RESET}")
            for enemy in enemies_in_room:
                ident = world.get_component(enemy, Identity)
                health = world.get_component(enemy, Health)
                if ident and health:
                    print(f"    {Color.RED}• {ident.name}{Color.RESET} {_hp_bar(health.current, health.maximum)}")

        print()

    def _render_player_stats(self, player: int, world: "World") -> None:
        ident = world.get_component(player, Identity)
        health = world.get_component(player, Health)
        cs = world.get_component(player, CombatStats)
        sfx = world.get_component(player, StatusEffects)

        name = ident.name if ident else "Hero"
        print(f"  {Color.BOLD}{Color.GREEN}{name}{Color.RESET}", end="  ")

        if health:
            print(f"HP: {_hp_bar(health.current, health.maximum)}", end="  ")

        if cs:
            print(f"{Color.CYAN}ATK:{Color.RESET} {cs.total_attack}  "
                  f"{Color.BLUE}DEF:{Color.RESET} {cs.total_defense}", end="")

        if sfx and sfx.effects:
            effect_names = ", ".join(e.name for e in sfx.effects)
            print(f"  {Color.MAGENTA}[{effect_names}]{Color.RESET}", end="")

        print()

    def _render_combat(self, world: "World", states) -> None:
        player = self._get_player(world)
        if not player:
            return

        combat_target = getattr(states, "combat_target", None)

        print(f"  {Color.BOLD}{Color.RED}⚔  COMBAT  ⚔{Color.RESET}\n")
        self._render_player_stats(player, world)

        if combat_target and world.entity_exists(combat_target):
            ident = world.get_component(combat_target, Identity)
            health = world.get_component(combat_target, Health)
            cs = world.get_component(combat_target, CombatStats)
            sfx = world.get_component(combat_target, StatusEffects)

            name = ident.name if ident else "Enemy"
            print(f"\n  {Color.BOLD}{Color.RED}{name}{Color.RESET}", end="  ")
            if health:
                print(f"HP: {_hp_bar(health.current, health.maximum)}", end="  ")
            if cs:
                print(f"ATK: {cs.total_attack}  DEF: {cs.total_defense}", end="")
            if sfx and sfx.effects:
                effect_names = ", ".join(e.name for e in sfx.effects)
                print(f"  [{effect_names}]", end="")
            print()

        print(f"\n  {Color.GRAY}Commands: attack | flee | use <item> | inventory{Color.RESET}")

    def _render_inventory(self, world: "World", states) -> None:
        player = self._get_player(world)
        if not player:
            return

        print(f"  {Color.BOLD}{Color.CYAN}INVENTORY{Color.RESET}\n")
        self._render_player_stats(player, world)
        print()

        inv = world.get_component(player, Inventory)
        eq = world.get_component(player, Equipment)

        # Equipped items
        if eq:
            print(f"  {Color.BOLD}Equipped:{Color.RESET}")
            for slot, item_id in eq.slots.items():
                if item_id is not None:
                    ident = world.get_component(item_id, Identity)
                    data = world.get_component(item_id, ItemData)
                    name = ident.name if ident else "Unknown"
                    bonuses = []
                    if data:
                        if data.attack_bonus: bonuses.append(f"+{data.attack_bonus} ATK")
                        if data.defense_bonus: bonuses.append(f"+{data.defense_bonus} DEF")
                    bonus_str = f" ({', '.join(bonuses)})" if bonuses else ""
                    print(f"    {Color.GRAY}[{slot}]{Color.RESET} {name}{bonus_str}")
            print()

        # Bag
        print(f"  {Color.BOLD}Bag ({inv.count if inv else 0}/{inv.capacity if inv else 0}):{Color.RESET}")
        if inv and inv.items:
            for i, item_id in enumerate(inv.items, 1):
                ident = world.get_component(item_id, Identity)
                data = world.get_component(item_id, ItemData)
                if ident:
                    rarity_color = RARITY_COLORS.get(data.rarity if data else "common", Color.WHITE)
                    info = []
                    if data:
                        if data.attack_bonus: info.append(f"+{data.attack_bonus} ATK")
                        if data.defense_bonus: info.append(f"+{data.defense_bonus} DEF")
                        if data.health_restore: info.append(f"+{data.health_restore} HP")
                        if data.consumable: info.append("consumable")
                        if data.slot: info.append(f"equip: {data.slot}")
                    info_str = f" ({', '.join(info)})" if info else ""
                    print(f"    {Color.GRAY}{i}.{Color.RESET} {rarity_color}{ident.name}{Color.RESET}{info_str}")
        else:
            print(f"    {Color.DIM}(empty){Color.RESET}")

        print(f"\n  {Color.GRAY}Commands: use <item> | equip <item> | unequip <slot> | drop <item> | back{Color.RESET}")

    def _render_main_menu(self) -> None:
        art = r"""
     ____  _   _ _   _  ____ _____ ___  _   _
    |  _ \| | | | \ | |/ ___| ____/ _ \| \ | |
    | | | | | | |  \| | |  _|  _|| | | |  \| |
    | |_| | |_| | |\  | |_| | |__| |_| | |\  |
    |____/ \___/|_| \_|\____|_____\___/|_| \_|
          C R A W L E R
        """
        print(f"{Color.YELLOW}{art}{Color.RESET}")
        print(f"  {Color.BOLD}[N]{Color.RESET} New Game")
        print(f"  {Color.BOLD}[L]{Color.RESET} Load Game")
        print(f"  {Color.BOLD}[Q]{Color.RESET} Quit")
        print()

    def _render_game_over(self) -> None:
        print(f"\n  {Color.BOLD}{Color.RED}YOU DIED{Color.RESET}\n")
        print(f"  {Color.BOLD}[R]{Color.RESET} Return to Menu")
        print()

    def _render_dialogue(self, world: "World", states) -> None:
        npc_target = getattr(states, "dialogue_target", None)
        if npc_target and world.entity_exists(npc_target):
            ident = world.get_component(npc_target, Identity)
            name = ident.name if ident else "Stranger"
            print(f"  {Color.BOLD}{Color.CYAN}Talking to {name}{Color.RESET}\n")
            if ident:
                print(f"  \"{ident.description}\"")
        print(f"\n  {Color.GRAY}Commands: quest | bye{Color.RESET}")

    def _render_message_log(self) -> None:
        if not self._message_log:
            return
        print(f"\n{Color.GRAY}{'─' * 60}{Color.RESET}")
        for text, category in self._message_log:
            color = CATEGORY_COLORS.get(category, Color.WHITE)
            print(f"  {color}{text}{Color.RESET}")
        print()

