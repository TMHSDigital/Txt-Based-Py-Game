class Enemy:
    def __init__(self, name, health, attack, defense, drop_items=[]):
        self.name = name
        self.health = health
        self.attack = attack
        self.defense = defense
        self.drop_items = drop_items

    def is_dead(self):
        return self.health <= 0
