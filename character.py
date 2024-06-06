class Character:
    def __init__(self, name, health, attack, defense):
        self.name = name
        self.health = health
        self.attack = attack
        self.defense = defense

    def is_alive(self):
        return self.health > 0

    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def attack_enemy(self, enemy):
        damage_dealt = self.attack - enemy.defense
        if damage_dealt < 0:
            damage_dealt = 0
        enemy.take_damage(damage_dealt)
        return damage_dealt
