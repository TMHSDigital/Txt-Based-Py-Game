import time
from character import Character

class Game:
    def __init__(self):
        self.player = None
        self.enemy = None

    def start(self):
        self.introduction()
        self.create_character()
        self.first_encounter()
        if self.player.is_alive():
            self.second_encounter()
        if self.player.is_alive():
            self.final_encounter()

    def introduction(self):
        print("Welcome to the Text-Based Adventure Game!")
        print("You will face various enemies and challenges.")
        print("Your goal is to survive and defeat all enemies.")
        time.sleep(2)

    def create_character(self):
        name = input("Enter your character's name: ")
        self.player = Character(name, health=100, attack=20, defense=10)
        print(f"{self.player.name} has been created with {self.player.health} health, {self.player.attack} attack, and {self.player.defense} defense.")

    def first_encounter(self):
        print("\nFirst Encounter: A wild goblin appears!")
        self.enemy = Character("Goblin", health=50, attack=10, defense=5)
        self.battle()

    def second_encounter(self):
        print("\nSecond Encounter: A fierce wolf attacks!")
        self.enemy = Character("Wolf", health=70, attack=15, defense=8)
        self.battle()

    def final_encounter(self):
        print("\nFinal Encounter: A mighty dragon blocks your path!")
        self.enemy = Character("Dragon", health=150, attack=25, defense=15)
        self.battle()

    def battle(self):
        while self.player.is_alive() and self.enemy.is_alive():
            print(f"\n{self.player.name}: {self.player.health} HP")
            print(f"{self.enemy.name}: {self.enemy.health} HP")
            action = input("Choose your action (attack/defend/run): ").lower()
            if action == "attack":
                damage = self.player.attack_enemy(self.enemy)
                print(f"You attack the {self.enemy.name} and deal {damage} damage.")
            elif action == "defend":
                self.player.defense += 5
                print(f"You brace yourself and increase your defense to {self.player.defense}.")
            elif action == "run":
                print("You run away from the battle!")
                return
            else:
                print("Invalid action. Please choose again.")
                continue

            if self.enemy.is_alive():
                damage = self.enemy.attack_enemy(self.player)
                print(f"The {self.enemy.name} attacks and deals {damage} damage to you.")

        if self.player.is_alive():
            print(f"\nYou have defeated the {self.enemy.name}!")
        else:
            print(f"\nYou have been defeated by the {self.enemy.name}... Game Over.")

if __name__ == "__main__":
    game = Game()
    game.start()
