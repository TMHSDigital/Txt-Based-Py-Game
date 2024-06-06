class Item:
    def __init__(self, name, description, item_type, health_bonus=0, attack_bonus=0, defense_bonus=0):
        self.name = name
        self.description = description
        self.type = item_type
        self.health_bonus = health_bonus
        self.attack_bonus = attack_bonus
        self.defense_bonus = defense_bonus

    def __str__(self):
        return self.name
