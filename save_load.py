import pickle

def save_game(player):
    with open('savegame.pkl', 'wb') as f:
        pickle.dump(player, f)

def load_game():
    with open('savegame.pkl', 'rb') as f:
        return pickle.load(f)
