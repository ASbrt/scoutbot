import random
from engine.state.CardCore import Card
from engine.state.GameState import GameState, Move, ShowMove, ScoutMove, ScoutAndShowMove

# TODO: Make Bot Interface? -> Different bot types could simply inherit the interface

class RandomBot:
    def choose_flip(self, hand: list[Card], player_index: int, rng: random.Random) -> bool:
        # 50/50 flip decision
        return rng.random() < 0.5

    def select_move(self, state: GameState, moves: list[Move], rng: random.Random) -> Move:
        # Partition moves by category
        show_moves = [m for m in moves if isinstance(m, ShowMove)]
        scout_moves = [m for m in moves if isinstance(m, ScoutMove)]
        scout_show_moves = [m for m in moves if isinstance(m, ScoutAndShowMove)]

        # If we can show, strongly prefer showing
        if show_moves:
            # 80% show, 20% others
            if rng.random() < 0.8:
                return rng.choice(show_moves)

            other_moves = scout_moves + scout_show_moves
            if other_moves:
                return rng.choice(other_moves)

            return rng.choice(show_moves)

        # If no show available, choose randomly among scout options
        return rng.choice(moves)