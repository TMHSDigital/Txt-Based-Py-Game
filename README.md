- - - - -- - - - Game Commands - - - - -- - - 
-Movement Commands
---north: Move north.
---south: Move south.
---east: Move east.
---west: Move west.
-Item Commands
---take <item>: Take an item from the room and add it to your inventory.
-Combat Commands
---attack <enemy>: Attack an enemy in the room.
-Game Management Commands
---save: Save the game.
---load: Load the game.
---quit: Exit the game.
- - - - -- - - - Features - - - - -- - - 
-Rooms
---Players can move between connected rooms.
---Each room can contain items and enemies.
-Items
---Items can be taken and added to the player's inventory.
---Items can have different effects, such as increasing attack, defense, or health.
-Enemies
---Enemies can be attacked by the player.
---Enemies can drop items upon defeat.
-Saving and Loading
---The game state can be saved and loaded.

- - - - -- - - - EXAMPLE GAMEPLAY - - - - -- - - 

markdown
Copy code
Enter your character's name: Paint
Start Room

This is the room you start in.

> north
You move north.
Second Room

This room has a sword in it.

You see the following items:
- Sword: A sharp looking sword

Enemies in this room:
- Goblin: 50 HP

> take sword
You take the sword.
Second Room

This room has a sword in it.

Enemies in this room:
- Goblin: 50 HP

> attack goblin
You attack the Goblin and deal 15 damage.
The Goblin attacks and deals 5 damage to you.

Second Room

This room has a sword in it.

Enemies in this room:
- Goblin: 35 HP

> attack goblin
You attack the Goblin and deal 15 damage.
The Goblin attacks and deals 5 damage to you.

Second Room

This room has a sword in it.

Enemies in this room:
- Goblin: 20 HP

> attack goblin
You attack the Goblin and deal 15 damage.
The Goblin attacks and deals 5 damage to you.

Second Room

This room has a sword in it.

Enemies in this room:
- Goblin: 5 HP

> attack goblin
You attack the Goblin and deal 15 damage.
You have defeated the Goblin!
The Goblin dropped the following items:
- Health Potion: A potion that restores health

> take health potion
You take the Health Potion.
Second Room

This room has a sword in it.

Enemies in this room:
- None

> south
You move south.
Start Room

This is the room you start in.

> save
Game saved.

> quit

<END OF GAMEPLAY>


yaml
Copy code

### To Run the Game
Use the following command:
```bash
python main.py
