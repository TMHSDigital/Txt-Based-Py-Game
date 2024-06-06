from room import Room

class Player:
    def __init__(self, name, start_room):
        self.name = name
        self.current_room = start_room
        self.inventory = []

    def move(self, direction):
        next_room = self.current_room.get_exit(direction)
        if next_room:
            self.current_room = next_room
            print(f"You move {direction}.")
        else:
            print("You can't go that way.")

    def take_item(self, item_name):
        item = self.current_room.remove_item(item_name)
        if item:
            self.inventory.append(item)
            print(f"You take the {item_name}.")
        else:
            print(f"There is no {item_name} here.")

    def drop_item(self, item_name):
        for item in self.inventory:
            if item.name.lower() == item_name:
                self.inventory.remove(item)
                self.current_room.add_item(item)
                print(f"You drop the {item_name}.")
                return
        print(f"You don't have a {item_name}.")
