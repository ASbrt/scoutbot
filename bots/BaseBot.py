"""
This is a shared bot interface for unifying bot handling. All Bots downstream from this can just inherit the
interface so that we make sure the API is the same everywhere. If i need to extend Bot functionality this also lets me do
it one convenient place.
"""

import random
from engine.state.CardCore import Card
from engine.state.GameState import GameState, Move

# Since this is just an interface it throws errors when the functions are called for it
class BaseBot:
    bot_key = None
    bot_label = None

    def __init__(self, name: str | None = None, verbose: bool = False):
        self.name = name or self.__class__.__name__
        self.verbose = verbose

    def choose_flip(self, hand: list[Card], player_index: int, rng: random.Random) -> bool:
        raise NotImplementedError

    def select_move(self, state: GameState, moves: list[Move], rng: random.Random) -> Move:
        raise NotImplementedError

# TODO: Integrate move partitioning here? Other shared helpers needed?