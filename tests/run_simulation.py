import random
from tests.testing import test_move_generation, test_scout_move, test_scout_and_show
from players.Bots import RandomBot
from engine.logic.GameLoop import play_game
import time

""" Leftover testing file - still runs since API did not change much, but not really used anymore"""

def testing():
    test_move_generation(seed=5, n_players=3)
    test_scout_move(seed=5,n_players=3)
    test_scout_and_show(seed=5, n_players=3)

def main():
    for i in range(3):
        rng = random.Random(i)
        n_players = 3
        bots = [RandomBot() for _ in range(n_players)]

        result = play_game(bots=bots, rng=rng, n_players=n_players, log_turns=True, game_id=0, seed=4321)

        print("\n=== FINAL RESULT ===")
        print("Final scores:", result.scores_final)
        time.sleep(1)


if __name__ == "__main__":
    main()


