"""
This is a HeuristicBot with an aggressive policy. It serves as a first progression point from RandomBot. The simple
aggressive policy is fairly easy to implement which is why this was chosen as the next step.

Flip decision values immediate power, it does not consider future connectivity of sets/runs. Same with Move decisions,
if there are moves available it always chooses the strongest possible.
"""

import random
from engine.state.CardCore import Card
from engine.state.GameState import GameState, Move
from engine.logic.helpers import flip_entire_hand, compute_hand_rank


class AggrHeuristicBot:
    def choose_flip(self, hand: list[Card], player_index: int, rng: random.Random) -> bool:
        """
        Based on computed total hand rank. True if hand quality after a flip is better than before the flip
        """
        hand_after_flip = flip_entire_hand(hand)

        hand_rank_before = compute_hand_rank(hand)
        hand_rank_after = compute_hand_rank(hand_after_flip)

        return hand_rank_after > hand_rank_before

    def select_move(self, state: GameState, moves: list[Move], rng: random.Random) -> Move:
        # Partition moves by category
        show_moves = [m for m in moves if isinstance(m, ShowMove)]
        scout_moves = [m for m in moves if isinstance(m, ScoutMove)]
        scout_show_moves = [m for m in moves if isinstance(m, ScoutAndShowMove)]

        if show_moves:
            strongest_move = sorted(show_moves, key=lambda move: move.candidate.rank)[-1]
            return strongest_move








        # If no show available, choose randomly among scout options
        return rng.choice(moves)