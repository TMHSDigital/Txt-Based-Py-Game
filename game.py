from player import Player
from room import Room
from item import Item
from enemy import Enemy
from save_load import save_game, load_game

def main():
    print("Enter your character's name: ")
    player_name = input("> ")
    player = Player(player_name, 100, 20, 10)

    # Create items
    sword = Item("Sword", "A sharp looking sword", attack=10)
    shield = Item("Shield", "A sturdy shield", defense=10)
    health_potion = Item("Health Potion", "A potion that restores health", health=20)

    # Create enemies
    goblin = Enemy("Goblin", 50, 10, 5, drop_items=[health_potion])
    wolf = Enemy("Wolf", 70, 15, 10, drop_items=[sword])
    dragon = Enemy("Dragon", 200, 50, 20, drop_items=[shield])

    # Create rooms
    start_room = Room("Start Room", "This is the room you start in.")
    second_room = Room("Second Room", "This room has a sword in it.")
    third_room = Room("Third Room", "This room has a shield in it.")
    fourth_room = Room("Fourth Room", "This room has a health potion in it.")
    boss_room = Room("Boss Room", "This room has a dragon in it.")

    # Connect rooms
    start_room.connect_room(second_room, "north")
    second_room.connect_room(start_room, "south")
    second_room.connect_room(third_room, "east")
    third_room.connect_room(second_room, "west")
    third_room.connect_room(fourth_room, "north")
    fourth_room.connect_room(third_room, "south")
    fourth_room.connect_room(boss_room, "east")
    boss_room.connect_room(fourth_room, "west")

    # Add items and enemies to rooms
    second_room.add_item(sword)
    third_room.add_item(shield)
    fourth_room.add_item(health_potion)
    second_room.add_enemy(goblin)
    third_room.add_enemy(wolf)
    boss_room.add_enemy(dragon)

    current_room = start_room

    while True:
        print(f"\n{current_room.name}\n")
        print(f"{current_room.description}\n")

        if current_room.items:
            print("You see the following items:")
            for item in current_room.items:
                print(f"- {item.name}: {item.description}")

        if current_room.enemies:
            print("\nEnemies in this room:")
            for enemy in current_room.enemies:
                print(f"- {enemy.name}: {enemy.health} HP")

        print("\n> ", end="")
        command = input().strip().lower()

        if command == "save":
            save_game(player, current_room)
            print("Game saved.")
        elif command == "load":
            player, current_room = load_game()
            print("Game loaded.")
        elif command == "quit":
            print("Goodbye!")
            break
        elif command in ["north", "south", "east", "west"]:
            next_room = current_room.move(command)
            if next_room:
                current_room = next_room
                print(f"You move {command}.")
            else:
                print("You can't go that way.")
        elif command.startswith("take "):
            item_name = command[5:]
            item = current_room.take_item(item_name)
            if item:
                player.add_item(item)
                print(f"You take the {item.name}.")
            else:
                print(f"There is no {item_name} here.")
        elif command.startswith("attack "):
            enemy_name = command[7:]
            enemy = current_room.get_enemy(enemy_name)
            if enemy:
                player.attack(enemy)
                if enemy.is_dead():
                    print(f"You have defeated the {enemy.name}!")
                    for item in enemy.drop_items:
                        current_room.add_item(item)
                    current_room.remove_enemy(enemy)
                else:
                    print(f"The {enemy.name} has {enemy.health} HP left.")
            else:
                print(f"There is no {enemy_name} here.")
        else:
            print("Unknown command. Try again.")

if __name__ == "__main__":
    main()
