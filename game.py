import pickle
from player import Player
from room import Room
from item import Item
from enemy import Enemy
from save_load import save_game, load_game

def main():
    # Create items
    sword = Item("Sword", "A sharp looking sword", "weapon", attack_bonus=10)
    shield = Item("Shield", "A sturdy shield", "armor", defense_bonus=5)
    health_potion = Item("Health Potion", "A potion that restores health", "health", health_bonus=20)

    # Create rooms
    start_room = Room("Start Room", "This is the room you start in.")
    second_room = Room("Second Room", "This room has a sword in it.")
    third_room = Room("Third Room", "This room has a shield in it.")
    base_camp = Room("Base Camp", "This is your base camp. You can save your progress here.")

    # Add items to rooms
    second_room.add_item(sword)
    third_room.add_item(shield)

    # Link rooms
    start_room.set_exit("north", second_room)
    second_room.set_exit("south", start_room)
    second_room.set_exit("east", third_room)
    third_room.set_exit("west", second_room)
    start_room.set_exit("west", base_camp)
    base_camp.set_exit("east", start_room)

    # Create enemies
    goblin = Enemy("Goblin", 50, 5, 2, [health_potion])
    wolf = Enemy("Wolf", 70, 10, 5, [sword])

    # Add enemies to rooms
    second_room.add_enemy(goblin)
    third_room.add_enemy(wolf)

    # Create player
    player_name = input("Enter your character's name: ")
    player = Player(player_name, start_room)

    # Game loop
    while True:
        print(player.current_room.get_description())
        command = input("> ").strip().lower()

        if command in ["quit", "exit"]:
            print("Thank you for playing!")
            break
        elif command == "save":
            save_game(player)
            print("Game saved!")
        elif command == "load":
            player = load_game()
            print(f"Welcome back, {player.name}!")
        elif command in ["north", "south", "east", "west"]:
            player.move(command)
        elif command.startswith("take "):
            item_name = command[5:]
            player.take_item(item_name)
        elif command.startswith("drop "):
            item_name = command[5:]
            player.drop_item(item_name)
        elif command == "attack":
            player.attack()
        else:
            print("Unknown command. Try again.")

if __name__ == "__main__":
    main()
