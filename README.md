# Dungeon Crawler

A text-based dungeon crawler written in Python, built on a clean
Entity-Component-System (ECS) architecture. The UI layer is fully
abstracted so the terminal frontend can be replaced with a graphical
renderer (Pygame, Godot export, etc.) without touching any game logic.

Python 3.10 or higher is required. There are no external dependencies.

---

## Table of Contents

- [Quickstart](#quickstart)
- [Gameplay](#gameplay)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Adding Content](#adding-content)
- [Data Schemas](#data-schemas)
- [Running Tests](#running-tests)
- [Upgrading the UI](#upgrading-the-ui)
- [Contributing](#contributing)

---

## Quickstart

```bash
git clone https://github.com/your-username/dungeon-crawler.git
cd dungeon-crawler
python main.py
```

No virtual environment or package installation is needed.

---

## Gameplay

You begin in Ironhaven, a frontier town on the edge of a dark forest.
Wolves stalk the road north. Goblins raid from the trees. Deep in the
ruins beyond the ravine, a lich commands the undead -- and behind it,
something far older stirs.

### World

```
Ironhaven (overworld hub)
  |-- Rusted Flagon Inn
  |-- Market
  |-- Garrison
  |-- Road to the Darkwood
        |-- Darkwood Edge
              |-- Darkwood Hollow  (goblin camp)
              |-- Darkwood Clearing
                    |-- Dire Wolf Den
                    |-- Ravine Path
                          |-- Ruins Entrance
                                |-- [The Ruins dungeon]
                                      |-- Entry Hall
                                      |-- Guard Room / Torture Chamber
                                      |-- Collapsed Corridor / Ruined Archive
                                      |-- Barracks / Commander's Quarters
                                      |-- Upper Vault
                                      |-- Lich's Sanctum
                                      |-- Dragon's Lair  (final boss)
```

### Commands

**Exploring**

| Command | Effect |
|---|---|
| `north` / `south` / `east` / `west` / `up` / `down` | Move in a direction |
| `look` | Redisplay the current room |
| `take <item>` | Pick up an item from the floor |
| `drop <item>` | Drop an item from your inventory |
| `use <item>` | Use a consumable item |
| `equip <item>` | Equip a weapon or piece of armor |
| `attack <enemy>` | Engage an enemy in combat |
| `inventory` or `i` | Open the inventory screen |
| `stats` | Display character statistics |
| `quests` | Open the quest journal |
| `save` | Save to slot 1 |
| `load` | Load from slot 1 |
| `help` | Print the command list |
| `quit` | Exit the game |

**Combat**

| Command | Effect |
|---|---|
| `attack` | Strike the current enemy |
| `flee` | Attempt to escape (60% success chance) |
| `use <item>` | Use a consumable; the enemy retaliates after |
| `inventory` | Peek at your inventory without ending the turn |

**Inventory screen**

| Command | Effect |
|---|---|
| `use <item>` | Use a consumable |
| `equip <item>` | Equip to the appropriate slot |
| `unequip <slot>` | Remove from a slot, e.g. `unequip main_hand` |
| `drop <item>` | Drop to the room floor |
| `back` | Return to the previous screen |

### Combat mechanics

- Turn order is determined by each combatant's Dexterity modifier.
- Damage formula: `(base_attack + STR_modifier + equipment_bonus + status_modifier - target_defense) * [0.85, 1.15]`, minimum 1.
- Enemies counterattack every round. Enemies at or below their `flee_threshold` HP percentage will attempt to escape.
- Status effects (poison, stun, strength boost, etc.) tick each turn and expire automatically.

---

## Architecture

The game is split into four independent layers that communicate only
through well-defined interfaces.

```
 +-----------+      +-----------+      +-----------+
 |  Content  |      |  Systems  |      |    UI     |
 |  (JSON)   | ---> | (logic)   | ---> | (render)  |
 +-----------+      +-----------+      +-----------+
       |                  |
       v                  v
 +-----------+      +-----------+
 |  Engine   | <--> |   World   |
 | (ECS core)|      | (registry)|
 +-----------+      +-----------+
```

**Engine** (`engine/`)  
The ECS runtime. `World` stores entities and components. `EventBus`
dispatches typed events between systems. `StateMachine` manages
game states (main menu, exploring, combat, inventory, dialogue,
game over). `GameLoop` drives the frame cycle: render -> input ->
update systems -> flush events.

**Components** (`components/`)  
Plain dataclasses with no logic dependencies. Each file groups related
components: `identity`, `spatial`, `combat`, `inventory`, `ai`, `quest`.
Components are the only shared data structure between systems.

**Systems** (`systems/`)  
Stateless functions that read and mutate components. Systems never
talk to each other directly; they publish events on the bus. The loot
system subscribes to `EntityDied`; the quest system subscribes to
`EntityDied`, `ItemPickedUp`, and `RoomEntered`; and so on.

**UI** (`ui/`)  
Two abstract base classes (`Renderer`, `InputHandler`) define the
interface. The `terminal/` package is the concrete implementation.
Replacing it with a graphical frontend requires only a new package
under `ui/` and a one-line change in `game_bootstrap.py`.

**Content pipeline** (`content/` + `data/`)  
`ContentLoader` reads the JSON data files and creates entities in the
world at startup. Entity factories in `content/templates.py` are the
canonical constructors for players, enemies, items, and rooms.

**Save system** (`saves/`)  
`SaveManager` serialises the full ECS world state to a human-readable
JSON file using `World.snapshot()` and restores it with
`World.restore()`. No pickle, no coupling to class internals.

---

## Project Structure

```
dungeon-crawler/
|
|-- main.py                   Entry point
|-- game_bootstrap.py         Wires engine, content, UI, and systems together
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|-- README.md
|
|-- engine/
|   |-- world.py              ECS registry: entities, components, tags, queries
|   |-- event_bus.py          Pub/sub bus + all typed event dataclasses
|   |-- state_machine.py      Game state definitions and transition logic
|   |-- game_loop.py          Main loop orchestration
|
|-- components/
|   |-- identity.py           Identity (name, description)
|   |-- spatial.py            Position, RoomData
|   |-- combat.py             Health, Stats, CombatStats, StatusEffects, Faction
|   |-- inventory.py          Inventory, Equipment, ItemData, RoomContents
|   |-- ai.py                 AIBehavior, LootTable, SpawnData
|   |-- quest.py              Quest, QuestLog, QuestObjective, QuestGiver
|
|-- systems/
|   |-- movement.py           Room transitions, exit wiring
|   |-- combat.py             Damage calculation, attack resolution, status ticks
|   |-- inventory.py          Pick up, drop, use, equip, unequip
|   |-- loot.py               Drop table resolution on enemy death
|   |-- ai.py                 Enemy behavior decisions (attack, flee, skip)
|   |-- spawn.py              Respawn timer tracking
|   |-- status_effects.py     Per-turn status effect processing
|   |-- quest.py              Objective tracking and completion
|
|-- ui/
|   |-- renderer.py           Abstract Renderer base class
|   |-- input_handler.py      Abstract InputHandler base class
|   |-- terminal/
|       |-- renderer.py       ANSI terminal renderer
|       |-- input_handler.py  stdin command parser and dispatcher
|
|-- content/
|   |-- loader.py             JSON loader, room registry, cross-zone exit resolution
|   |-- templates.py          Entity factory functions
|
|-- data/
|   |-- config.json           Balance constants and player defaults
|   |-- items.json            Item templates
|   |-- enemies.json          Enemy templates
|   |-- quests.json           Quest definitions
|   |-- rooms/
|       |-- overworld.json    Ironhaven and the Darkwood
|       |-- dungeon_01.json   The Ruins dungeon
|
|-- saves/
|   |-- save_manager.py       JSON save/load via world snapshot
|   |-- slot1.json            (created at runtime)
|
|-- tests/
    |-- test_world.py
    |-- test_combat.py
    |-- test_inventory.py
```

---

## Adding Content

All game content is data-driven. No Python changes are required to add
new rooms, enemies, items, or quests.

### Add a room

Open `data/rooms/overworld.json` (or `dungeon_01.json`) and add an entry
under `"rooms"`:

```json
"my_new_room": {
  "name": "Display Name",
  "description": "What the player reads when they enter.",
  "exits": {
    "north": "adjacent_room_key",
    "east": "other_zone:room_in_other_zone"
  },
  "items": ["health_potion"],
  "enemies": ["goblin"]
}
```

Cross-zone exits use the `"zone:room_key"` format. Same-zone exits use
just the room key.

### Add an enemy

Open `data/enemies.json` and add a top-level key:

```json
"shadow_wolf": {
  "name": "Shadow Wolf",
  "description": "A wolf wreathed in darkness.",
  "health": 80,
  "stats": { "strength": 12, "dexterity": 15, "constitution": 10, "intelligence": 5 },
  "base_attack": 14,
  "base_defense": 5,
  "ai": "aggressive",
  "flee_threshold": 0.15,
  "faction": "beasts",
  "loot_table": {
    "entries": [
      { "item_id": "health_potion", "chance": 0.4 },
      { "item_id": "gold_coins", "chance": 0.9, "quantity_min": 5, "quantity_max": 20 }
    ],
    "guaranteed": []
  },
  "respawn_turns": 0,
  "xp_reward": 90
}
```

Then reference `"shadow_wolf"` in the `"enemies"` list of any room.

### Add an item

Open `data/items.json` and add a top-level key:

```json
"silver_dagger": {
  "name": "Silver Dagger",
  "description": "Effective against the undead.",
  "item_type": "weapon",
  "slot": "main_hand",
  "attack_bonus": 6,
  "defense_bonus": 0,
  "value": 35,
  "rarity": "uncommon"
}
```

### Add a quest

Open `data/quests.json` and add a top-level key:

```json
"lost_shipment": {
  "title": "Lost Shipment",
  "description": "A merchant's wagon was taken by goblins.",
  "objectives": [
    {
      "objective_id": "kill_thieves",
      "description": "Defeat goblins in the Darkwood",
      "objective_type": "kill",
      "target_id": "goblin",
      "required_count": 3
    }
  ],
  "reward_xp": 80,
  "reward_gold": 40,
  "reward_items": []
}
```

---

## Data Schemas

### `data/config.json`

```
player.starting_health         int    Starting HP
player.starting_stats          object STR / DEX / CON / INT values
player.base_attack             int    Base attack before equipment
player.base_defense            int    Base defense before equipment
player.inventory_capacity      int    Maximum item slots
player.starting_room           string "zone:room_key" of the starting room
player.starting_items          array  List of item_ids given at game start

combat.damage_variance_min     float  Lower bound of damage roll multiplier
combat.damage_variance_max     float  Upper bound of damage roll multiplier
combat.flee_success_chance     float  Probability a player flee attempt succeeds
combat.minimum_damage          int    Floor on all damage calculations

difficulty.enemy_health_*      float  Global multipliers for balancing
```

### `data/items.json`

Each key is an `item_id` referenced by loot tables, room definitions,
quest rewards, and config starting items.

```
name               string  Display name
description        string  Flavour text shown in room and inventory
item_type          string  "weapon" | "armor" | "consumable" | "misc"
slot               string  Equipment slot, or "" if not equippable
                           Valid slots: head, chest, legs, feet,
                                        main_hand, off_hand, ring, neck
attack_bonus       int     Added to total_attack when equipped
defense_bonus      int     Added to total_defense when equipped
health_restore     int     HP restored when used (consumables)
max_health_bonus   int     Maximum HP increase when equipped
consumable         bool    If true, the item is destroyed on use
stackable          bool    Reserved for future stack merging logic
quantity           int     Default stack size
value              int     Gold value (for future shop systems)
rarity             string  "common" | "uncommon" | "rare" | "epic" | "legendary"
on_use_effects     array   Status effects applied on use (see below)
```

`on_use_effects` entry:

```
name               string  Identifier shown to the player
duration           int     Number of turns the effect lasts
damage_per_turn    int     HP removed each turn (poison)
heal_per_turn      int     HP restored each turn (regeneration)
attack_modifier    int     Flat attack bonus while active
defense_modifier   int     Flat defense bonus while active
is_stun            bool    If true, target cannot attack
```

### `data/enemies.json`

Each key is a `template_id` referenced by room definitions and the spawn
system.

```
name               string  Display name
description        string  Shown when the enemy appears
health             int     Starting and maximum HP
stats.strength     int     Affects STR damage modifier
stats.dexterity    int     Determines initiative order
stats.constitution int     Reserved for future HP scaling
stats.intelligence int     Reserved for future spell systems
base_attack        int     Base damage before modifiers
base_defense       int     Flat damage reduction
ai                 string  "aggressive" | "passive" | "coward"
flee_threshold     float   HP fraction at which the enemy flees
faction            string  "monsters" | "undead" | "beasts" | "neutral"
loot_table         object  See loot table schema below
respawn_turns      int     Turns until the enemy respawns (0 = never)
xp_reward          int     Reserved for future XP systems
```

`loot_table`:

```
entries[].item_id       string  Item template key
entries[].chance        float   0.0 to 1.0 drop probability
entries[].quantity_min  int     Minimum quantity dropped
entries[].quantity_max  int     Maximum quantity dropped
guaranteed              array   Item keys that always drop
```

### `data/quests.json`

```
title              string  Short display title
description        string  Full quest description
objectives         array   See objective schema below
reward_xp          int     Experience points on completion
reward_gold        int     Gold awarded on completion
reward_items       array   Item keys added to inventory on completion
```

`objectives` entry:

```
objective_id       string  Unique identifier within the quest
description        string  Progress text shown in the journal
objective_type     string  "kill" | "collect" | "visit" | "talk"
target_id          string  template_id of the target enemy, item, or room
required_count     int     How many times the objective must be met
```

### Room files (`data/rooms/*.json`)

```
zone               string  Zone identifier, e.g. "overworld" or "dungeon_01"
rooms              object  Map of room_key -> room definition
```

Room definition:

```
name               string  Display name
description        string  Shown when the player enters the room
exits              object  direction -> "zone:room_key" or "room_key"
items              array   Item keys placed on the floor at startup
enemies            array   Enemy template keys spawned at startup
is_safe            bool    (optional) Reserved for no-combat zones
```

---

## Running Tests

```bash
python tests/test_world.py
python tests/test_combat.py
python tests/test_inventory.py
```

All three test modules are self-contained and can be run individually.
The test suite covers the ECS registry, combat damage and status
effects, and the full inventory lifecycle (pick up, drop, use, equip,
unequip).

---

## Upgrading the UI

The `Renderer` and `InputHandler` abstract base classes in `ui/` define
the contract the game loop depends on. To replace the terminal frontend
with a graphical one:

1. Create a new package, e.g. `ui/pygame/`.
2. Implement `ui/pygame/renderer.py` by subclassing `ui.renderer.Renderer`.
3. Implement `ui/pygame/input_handler.py` by subclassing `ui.input_handler.InputHandler`.
4. In `game_bootstrap.py`, replace the two import lines and the two
   instantiation lines for `TerminalRenderer` and `TerminalInputHandler`.

No other file changes are required. Systems, components, and the engine
are entirely UI-agnostic.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
