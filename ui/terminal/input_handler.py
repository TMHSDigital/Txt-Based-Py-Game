"""
Terminal input handler - stdin command parser and dispatcher.

:class:`TerminalInputHandler` reads one line of text from stdin per
frame and routes it to the appropriate per-state handler method.

Each handler method (``_handle_exploring``, ``_handle_combat``, etc.)
maps command strings to calls into the game systems. Commands are always
lowercased before matching so input is case-insensitive. Partial name
matching (``"take sw"`` matches ``"Sword"``) is implemented in the
inventory system's search helpers.

Feedback generated during a frame is forwarded to the renderer via the
``relay_message`` subscription registered in ``game_bootstrap``, which
calls ``renderer.show_message`` for every ``MessagePosted`` event so
messages appear on the very next render call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World
    from engine.state_machine import StateMachine
    from engine.event_bus import EventBus

from ui.input_handler import InputHandler
from engine.event_bus import MessagePosted, CombatEnded, GameStateChanged
from systems.movement import move_entity, VALID_DIRECTIONS
from systems import inventory as inv_sys
from systems import combat as combat_sys
from systems import ai as ai_sys
from components.spatial import Position
from components.combat import Health, CombatStats
from components.inventory import Inventory, Equipment, ItemData
from components.quest import QuestLog, QuestStatus
from components.identity import Identity


HELP_TEXT = {
    "exploring": """\
  Movement : north | south | east | west | up | down
  Items    : take <item> | drop <item> | use <item> | equip <item>
  Info     : look | inventory (i) | stats | quests
  System   : save | load | help | quit
""",
    "combat": """\
  attack           - Strike the enemy
  use <item>       - Use a consumable item
  flee             - Attempt to escape
  inventory (i)    - Open inventory mid-combat
""",
    "inventory": """\
  use <item>       - Use a consumable
  equip <item>     - Equip a weapon or armor
  unequip <slot>   - Remove equipped item
  drop <item>      - Drop item to floor
  back             - Return to previous state
""",
}


class TerminalInputHandler(InputHandler):
    """
    Reads commands from stdin and dispatches them to state handlers.

    ``game_loop`` is required so that commands like ``quit`` and the
    main menu new-game flow can call :meth:`~engine.game_loop.GameLoop.stop`.
    ``renderer`` is required so that messages generated during handling
    can be forwarded to the on-screen log before the next render call.
    """

    def __init__(self, game_loop, renderer) -> None:
        self._loop = game_loop
        self._renderer = renderer

    def get_input(self, state: str) -> str:
        """Display a state-appropriate prompt and block until the user presses Enter."""
        if state == "main_menu":
            prompt = "\n  > "
        elif state == "combat":
            prompt = f"\n  [Combat] > "
        elif state == "inventory":
            prompt = f"\n  [Inventory] > "
        else:
            prompt = "\n  > "
        return input(prompt).strip().lower()

    def handle(
        self,
        raw: str,
        state: str,
        world: "World",
        states: "StateMachine",
        bus: "EventBus",
    ) -> None:
        if state == "main_menu":
            self._handle_main_menu(raw, world, states, bus)
        elif state == "exploring":
            self._handle_exploring(raw, world, states, bus)
        elif state == "combat":
            self._handle_combat(raw, world, states, bus)
        elif state == "inventory":
            self._handle_inventory(raw, world, states, bus)
        elif state == "dialogue":
            self._handle_dialogue(raw, world, states, bus)
        elif state == "game_over":
            self._handle_game_over(raw, world, states, bus)

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _handle_main_menu(self, cmd: str, world, states, bus) -> None:
        from content.loader import ContentLoader
        from saves.save_manager import SaveManager

        if cmd in ("n", "new", "new game"):
            states.transition("exploring")
        elif cmd in ("l", "load", "load game"):
            save_mgr = SaveManager(world)
            if save_mgr.load("saves/slot1.json"):
                bus.publish_immediate(MessagePosted("Game loaded.", "success"))
                states.transition("exploring")
            else:
                bus.publish_immediate(MessagePosted("No save file found.", "warning"))
        elif cmd in ("q", "quit"):
            self._loop.stop()
        else:
            bus.publish_immediate(MessagePosted("Commands: [N]ew Game  [L]oad  [Q]uit", "info"))

    def _handle_exploring(self, cmd: str, world, states, bus) -> None:
        player = self._get_player(world)
        if player is None:
            return

        # Movement
        if cmd in VALID_DIRECTIONS:
            move_entity(player, cmd, world, bus)
            return

        # Look
        if cmd in ("look", "l"):
            # Redisplay is handled by render; just re-trigger a render pass
            return

        # Inventory
        if cmd in ("inventory", "i", "inv"):
            states.transition("inventory")
            return

        # Stats
        if cmd == "stats":
            self._print_stats(player, world, bus)
            return

        # Quests
        if cmd in ("quests", "quest", "q", "journal"):
            self._print_quests(player, world, bus)
            return

        # Take
        if cmd.startswith("take ") or cmd.startswith("pick up "):
            item_name = cmd.split(" ", 1)[1]
            pos = world.get_component(player, Position)
            if pos:
                item_id = inv_sys.get_item_in_room_by_name(item_name, pos.room_id, world)
                if item_id:
                    inv_sys.pick_up_item(player, item_id, world, bus)
                else:
                    bus.publish_immediate(MessagePosted(f"No '{item_name}' here.", "warning"))
            return

        # Drop
        if cmd.startswith("drop "):
            item_name = cmd[5:]
            item_id = inv_sys.get_item_in_inventory_by_name(item_name, player, world)
            if item_id:
                inv_sys.drop_item(player, item_id, world, bus)
            else:
                bus.publish_immediate(MessagePosted(f"You don't have '{item_name}'.", "warning"))
            return

        # Use
        if cmd.startswith("use "):
            item_name = cmd[4:]
            item_id = inv_sys.get_item_in_inventory_by_name(item_name, player, world)
            if item_id:
                inv_sys.use_item(player, item_id, world, bus)
            else:
                bus.publish_immediate(MessagePosted(f"You don't have '{item_name}'.", "warning"))
            return

        # Equip
        if cmd.startswith("equip "):
            item_name = cmd[6:]
            item_id = inv_sys.get_item_in_inventory_by_name(item_name, player, world)
            if item_id:
                inv_sys.equip_item(player, item_id, world, bus)
            else:
                bus.publish_immediate(MessagePosted(f"You don't have '{item_name}'.", "warning"))
            return

        # Attack -> transition to combat
        if cmd in ("attack", "fight"):
            # Bare attack with no target: auto-engage if exactly one enemy in room
            pos = world.get_component(player, Position)
            enemies_here = [
                e for e in world.entities_with_tag("enemy")
                if (ep := world.get_component(e, Position)) and ep.room_id == pos.room_id
                and (eh := world.get_component(e, Health)) and not eh.is_dead()
            ] if pos else []
            if len(enemies_here) == 1:
                enemy = enemies_here[0]
                states.combat_target = enemy
                states.transition("combat")
                bus.publish_immediate(MessagePosted(
                    f"You engage the {self._ename(enemy, world)}!", "combat"
                ))
            elif len(enemies_here) > 1:
                names = ", ".join(self._ename(e, world) for e in enemies_here)
                bus.publish_immediate(MessagePosted(f"Who do you attack? ({names})", "warning"))
            else:
                bus.publish_immediate(MessagePosted("No enemies here.", "warning"))
            return

        if cmd.startswith("attack ") or cmd.startswith("fight "):
            parts = cmd.split(" ", 1)
            enemy_name = parts[1] if len(parts) > 1 else ""
            enemy = self._find_enemy_in_room(enemy_name, player, world)
            if enemy:
                states.combat_target = enemy
                states.transition("combat")
                bus.publish_immediate(MessagePosted(
                    f"You engage the {self._ename(enemy, world)}!", "combat"
                ))
            else:
                bus.publish_immediate(MessagePosted(f"No enemy named '{enemy_name}' here.", "warning"))
            return

        # Save
        if cmd == "save":
            from saves.save_manager import SaveManager
            SaveManager(world).save("saves/slot1.json")
            bus.publish_immediate(MessagePosted("Game saved.", "success"))
            return

        # Load
        if cmd == "load":
            from saves.save_manager import SaveManager
            if SaveManager(world).load("saves/slot1.json"):
                bus.publish_immediate(MessagePosted("Game loaded.", "success"))
            else:
                bus.publish_immediate(MessagePosted("No save file found.", "warning"))
            return

        # Help
        if cmd in ("help", "?", "h"):
            bus.publish_immediate(MessagePosted(HELP_TEXT["exploring"], "info"))
            return

        # Quit
        if cmd in ("quit", "exit", "q"):
            self._loop.stop()
            return

        bus.publish_immediate(MessagePosted(f"Unknown command: '{cmd}'. Type 'help' for commands.", "warning"))

    def _handle_combat(self, cmd: str, world, states, bus) -> None:
        player = self._get_player(world)
        enemy = getattr(states, "combat_target", None)

        if enemy is None or not world.entity_exists(enemy):
            states.transition("exploring")
            return

        enemy_health = world.get_component(enemy, Health)
        if enemy_health and enemy_health.is_dead():
            states.transition("exploring")
            return

        # Attack
        if cmd in ("attack", "a", "fight", "hit", "strike"):
            result = combat_sys.run_combat_round(player, enemy, world, bus)
            bus.flush()
            if result == "player_won":
                states.combat_target = None
                states.transition("exploring")
            elif result == "player_died":
                states.transition("game_over")
            return

        # Flee
        if cmd in ("flee", "run", "escape"):
            import random
            if random.random() < 0.6:
                bus.publish_immediate(MessagePosted("You escape from combat!", "info"))
                states.combat_target = None
                states.transition("exploring")
            else:
                bus.publish_immediate(MessagePosted("You can't escape!", "warning"))
                # Enemy still attacks
                combat_sys.resolve_attack(enemy, player, world, bus)
                player_health = world.get_component(player, Health)
                if player_health and player_health.is_dead():
                    states.transition("game_over")
            return

        # Use item during combat
        if cmd.startswith("use "):
            item_name = cmd[4:]
            item_id = inv_sys.get_item_in_inventory_by_name(item_name, player, world)
            if item_id:
                inv_sys.use_item(player, item_id, world, bus)
                # Enemy gets a free attack after you use an item
                combat_sys.resolve_attack(enemy, player, world, bus)
                player_health = world.get_component(player, Health)
                if player_health and player_health.is_dead():
                    states.transition("game_over")
            else:
                bus.publish_immediate(MessagePosted(f"You don't have '{item_name}'.", "warning"))
            return

        # Inventory peek during combat
        if cmd in ("inventory", "i", "inv"):
            states.transition("inventory")
            return

        if cmd in ("help", "?"):
            bus.publish_immediate(MessagePosted(HELP_TEXT["combat"], "info"))
            return

        bus.publish_immediate(MessagePosted("Commands: attack | flee | use <item> | help", "warning"))

    def _handle_inventory(self, cmd: str, world, states, bus) -> None:
        player = self._get_player(world)
        if player is None:
            return

        if cmd in ("back", "b", "close", "exit", "esc"):
            # Return to previous state
            prev = "combat" if getattr(states, "combat_target", None) else "exploring"
            states.transition(prev)
            return

        if cmd.startswith("use "):
            item_name = cmd[4:]
            item_id = inv_sys.get_item_in_inventory_by_name(item_name, player, world)
            if item_id:
                inv_sys.use_item(player, item_id, world, bus)
            else:
                bus.publish_immediate(MessagePosted(f"You don't have '{item_name}'.", "warning"))
            return

        if cmd.startswith("equip "):
            item_name = cmd[6:]
            item_id = inv_sys.get_item_in_inventory_by_name(item_name, player, world)
            if item_id:
                inv_sys.equip_item(player, item_id, world, bus)
            else:
                bus.publish_immediate(MessagePosted(f"You don't have '{item_name}'.", "warning"))
            return

        if cmd.startswith("unequip "):
            slot = cmd[8:]
            inv_sys.unequip_item(player, slot, world, bus)
            return

        if cmd.startswith("drop "):
            item_name = cmd[5:]
            item_id = inv_sys.get_item_in_inventory_by_name(item_name, player, world)
            if item_id:
                inv_sys.drop_item(player, item_id, world, bus)
            else:
                bus.publish_immediate(MessagePosted(f"You don't have '{item_name}'.", "warning"))
            return

        if cmd in ("help", "?"):
            bus.publish_immediate(MessagePosted(HELP_TEXT["inventory"], "info"))
            return

        bus.publish_immediate(MessagePosted("Commands: use | equip | unequip | drop | back | help", "warning"))

    def _handle_dialogue(self, cmd: str, world, states, bus) -> None:
        if cmd in ("bye", "leave", "back", "exit"):
            states.dialogue_target = None
            states.transition("exploring")
            return

        if cmd in ("quest", "quests"):
            npc = getattr(states, "dialogue_target", None)
            if npc:
                from components.quest import QuestGiver
                giver = world.get_component(npc, QuestGiver)
                if giver and giver.quest_ids:
                    player = self._get_player(world)
                    log = world.get_component(player, QuestLog)
                    for qid in giver.quest_ids:
                        quest = log.get_quest(qid) if log else None
                        if quest and quest.status == QuestStatus.AVAILABLE:
                            quest.status = QuestStatus.ACTIVE
                            bus.publish_immediate(MessagePosted(
                                f"Quest accepted: {quest.title}", "quest"
                            ))
            return

        bus.publish_immediate(MessagePosted("Commands: quest | bye", "info"))

    def _handle_game_over(self, cmd: str, world, states, bus) -> None:
        if cmd in ("r", "restart", "menu", "return"):
            states.transition("main_menu")
        else:
            bus.publish_immediate(MessagePosted("[R] Return to Menu", "info"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_player(self, world) -> int | None:
        players = world.entities_with_tag("player")
        return players[0] if players else None

    def _find_enemy_in_room(self, name_query: str, player: int, world) -> int | None:
        pos = world.get_component(player, Position)
        if not pos:
            return None
        for enemy in world.entities_with_tag("enemy"):
            epos = world.get_component(enemy, Position)
            if epos and epos.room_id == pos.room_id:
                ehealth = world.get_component(enemy, Health)
                if ehealth and not ehealth.is_dead():
                    ident = world.get_component(enemy, Identity)
                    if ident and name_query.lower() in ident.name.lower():
                        return enemy
        return None

    def _ename(self, entity: int, world) -> str:
        ident = world.get_component(entity, Identity)
        return ident.name if ident else "enemy"

    def _print_stats(self, player: int, world, bus) -> None:
        from components.combat import Stats
        ident = world.get_component(player, Identity)
        health = world.get_component(player, Health)
        stats = world.get_component(player, Stats)
        cs = world.get_component(player, CombatStats)
        inv = world.get_component(player, Inventory)

        lines = [f"=== {ident.name if ident else 'Hero'} ==="]
        if health:
            lines.append(f"HP: {health.current}/{health.maximum}")
        if stats:
            lines.append(f"STR:{stats.strength} DEX:{stats.dexterity} CON:{stats.constitution} INT:{stats.intelligence}")
        if cs:
            lines.append(f"Attack: {cs.total_attack}  Defense: {cs.total_defense}")
        if inv:
            lines.append(f"Inventory: {inv.count}/{inv.capacity} items")
        bus.publish_immediate(MessagePosted("\n".join(lines), "info"))

    def _print_quests(self, player: int, world, bus) -> None:
        log = world.get_component(player, QuestLog)
        if not log or not log.quests:
            bus.publish_immediate(MessagePosted("No quests yet.", "info"))
            return
        lines = ["=== Quest Journal ==="]
        for quest in log.quests.values():
            status_icon = {"active": "►", "completed": "✓", "available": "○", "failed": "✗"}.get(quest.status, "?")
            lines.append(f"{status_icon} {quest.title} [{quest.status}]")
            for obj in quest.objectives:
                done = "✓" if obj.is_complete else " "
                lines.append(f"   [{done}] {obj.description} ({obj.current_count}/{obj.required_count})")
        bus.publish_immediate(MessagePosted("\n".join(lines), "quest"))
