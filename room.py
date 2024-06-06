class Room:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.exits = {}
        self.items = []
        self.enemies = []

    def set_exit(self, direction, room):
        self.exits[direction] = room

    def get_exit(self, direction):
        return self.exits.get(direction, None)

    def get_description(self):
        desc = f"{self.name}\n\n{self.description}\n"
        if self.items:
            desc += "\nYou see the following items:\n"
            for item in self.items:
                desc += f"- {item.name}: {item.description}\n"
        if self.enemies:
            desc += "\nEnemies in this room:\n"
            for enemy in self.enemies:
                desc += f"- {enemy.name}: {enemy.health} HP\n"
        return desc

    def add_item(self, item):
        self.items.append(item)

    def remove_item(self, item_name):
        for item in self.items:
            if item.name.lower() == item_name:
                self.items.remove(item)
                return item
        return None

    def add_enemy(self, enemy):
        self.enemies.append(enemy)
