class Player:
    def __init__(self, name, health, attack, defense):
        self.name = name
        self.health = health
        self.attack_power = attack
        self.defense = defense
        self.inventory = []

    def add_item(self, item):
        self.inventory.append(item)
        if item.attack:
            self.attack_power += item.attack
        if item.defense:
            self.defense += item.defense
        if item.health:
            self.health += item.health

    def attack(self, enemy):
        damage = self.attack_power - enemy.defense
        if damage > 0:
            enemy.health -= damage
            print(f"You attack the {enemy.name} and deal {damage} damage.")
        else:
            print(f"Your attack is too weak to harm the {enemy.name}.")

    def is_dead(self):
        return self.health <= 0
