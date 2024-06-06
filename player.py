from room import Room

class Player:
    def __init__(self, name, start_room):
        self.name = name
        self.current_room = start_room
        self.inventory = []
        self.health = 100
        self.attack = 20
        self.defense = 10

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

    def attack(self):
        if self.current_room.enemies:
            enemy = self.current_room.enemies[0]
            damage = self.attack - enemy.defense
            if damage < 0:
                damage = 0
            enemy.health -= damage
            print(f"You attack the {enemy.name} and deal {damage} damage.")
            if enemy.health <= 0:
                print(f"You have defeated the {enemy.name}!")
                self.current_room.enemies.remove(enemy)
                self.collect_drops(enemy)
            else:
                enemy_attack = enemy.attack - self.defense
                if enemy_attack < 0:
                    enemy_attack = 0
                self.health -= enemy_attack
                print(f"The {enemy.name} attacks and deals {enemy_attack} damage to you.")
        else:
            print("There are no enemies here.")

    def collect_drops(self, enemy):
        if enemy.drops:
            for item in enemy.drops:
                self.inventory.append(item)
                print(f"The {enemy.name} dropped {item.name}. You have collected it.")

    def show_inventory(self):
        print("Your inventory:")
        for item in self.inventory:
            print(f"- {item.name}: {item.description}")

    def use_item(self, item_name):
        for item in self.inventory:
            if item.name.lower() == item_name:
                if item.type == "health":
                    self.health += item.health_bonus
                    print(f"You used {item.name} and restored {item.health_bonus} health.")
                    self.inventory.remove(item)
                elif item.type == "weapon":
                    self.attack += item.attack_bonus
                    print(f"You equipped {item.name}. Attack increased by {item.attack_bonus}.")
                    self.inventory.remove(item)
                elif item.type == "armor":
                    self.defense += item.defense_bonus
                    print(f"You equipped {item.name}. Defense increased by {item.defense_bonus}.")
                    self.inventory.remove(item)
                return
        print(f"You don't have a {item_name}.")
