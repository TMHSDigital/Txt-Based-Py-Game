# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [0.2.0] - 2026-02-22

Complete architectural rewrite. The original ~220-line procedural script
has been replaced with a modular ECS engine.

### Added

- Entity-Component-System engine (`engine/world.py`) with integer entity
  IDs, type-keyed component storage, tag system, and multi-component
  queries.
- Pub/sub event bus (`engine/event_bus.py`) with deferred and immediate
  dispatch modes. Sixteen typed event dataclasses covering combat,
  inventory, movement, quests, and state changes.
- Game state machine (`engine/state_machine.py`) with validated
  transitions between MainMenu, Exploring, Combat, Inventory, Dialogue,
  and GameOver states.
- Game loop (`engine/game_loop.py`) with per-state and always-on system
  hooks.
- Component library: Identity, Position, RoomData, Health, Stats,
  CombatStats, StatusEffect/StatusEffects, Faction, Inventory,
  Equipment, ItemData, RoomContents, AIBehavior, LootTable, SpawnData,
  Quest, QuestLog, QuestObjective, QuestGiver.
- Full turn-based combat system with dexterity-based initiative, STR
  modifier and equipment bonuses, damage variance, enemy counterattack,
  stun handling, and player/enemy death events.
- Status effects system: poison, stun, strength boost, regeneration.
  Effects tick each turn and expire automatically.
- Inventory system: pick up, drop, use (consumable destruction), equip
  (with slot displacement), unequip (with inventory capacity check).
  Equipment bonuses applied and removed from CombatStats.
- Loot system: event-driven drop table resolution on EntityDied.
  Supports guaranteed drops, chance-based drops, and quantity ranges.
- Quest system: kill, collect, and visit objective types tracked via
  event subscriptions. Completion detection and reward announcement.
- AI system: aggressive, passive, and coward behavior types. Flee
  behavior triggered at configurable HP threshold.
- Spawn tracking component with per-enemy respawn timer.
- Movement system with validated room transitions and bidirectional exit
  wiring helper.
- JSON content pipeline: ContentLoader reads data files and populates
  the world. Cross-zone room references use "zone:room_key" format.
  Entity factories in content/templates.py are the canonical
  constructors for all entity types.
- Data files: 21 rooms across two zones (Ironhaven overworld and The
  Ruins dungeon), 9 enemy templates (goblin to dragon), 24 item
  templates (weapons, armor, consumables, stat items), 5 quests.
- JSON save system replacing pickle. Full world state serialised via
  World.snapshot() and restored via World.restore() with a component
  registry. Human-readable, safe across class refactors.
- ANSI terminal renderer with HP bars, rarity-coloured items, per-turn
  message log, and distinct colour coding for combat, loot, quest, and
  system messages.
- Terminal input handler with state-aware command dispatch for all six
  game states.
- Abstract Renderer and InputHandler base classes to allow UI
  replacement without modifying game logic.
- Unit tests for the ECS world (9 tests), combat system (4 tests), and
  inventory system (5 tests). All 18 pass.
- CONTRIBUTING.md and CHANGELOG.md.

### Removed

- Original `game.py`, `player.py`, `character.py`, `enemy.py`,
  `item.py`, `room.py`, `save_load.py`. All functionality has been
  reimplemented in the new architecture.

### Fixed

- `Room` was missing `connect_room`, `move`, `take_item`, `get_enemy`,
  and `remove_enemy` -- methods called by `game.py` but never defined.
  The game could not run at all.
- `save_game` accepted one argument but was called with two; `load_game`
  returned one value but was unpacked as two.
- Enemies never counterattacked. Combat was entirely one-sided.
- No player death handling. The game loop had no game-over state.
- `drop_items=[]` mutable default argument in `Enemy.__init__`.
- `character.py` was dead code; neither `Player` nor `Enemy` inherited
  from `Character`.
- Room descriptions were static strings and did not reflect items taken
  or enemies defeated.
- `save_load.py` used `pickle`, which is insecure and breaks when class
  definitions change.

---

## [0.1.0] - initial

Original proof-of-concept. Five rooms, three enemies, three items,
broken save system, no enemy counterattack.
