class Character:
    def __init__(self, name, health, attack, defense):
        self.name = name
        self.health = health
        self.attack = attack
        self.defense = defense

    def is_dead(self):
        return self.health <= 0

    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0
