"""
This is a HeuristicBot with an aggressive policy. It serves as a first progression point from RandomBot. The simple
aggressive policy is fairly easy to implement which is why this was chosen as the next step.

Flip decision values immediate power, it does not consider future connectivity of sets/runs. Same with Move decisions,
if there are moves available it always chooses the strongest possible.
"""

import random
from engine.logic.legal_moves import apply_move
from engine.state.CardCore import Card
from engine.state.GameState import GameState, Move, ScoutMove, ScoutAndShowMove, ShowMove
from engine.logic.helpers import flip_entire_hand, compute_hand_rank
from ..BaseBot import BaseBot


class AggrHeuristicBot(BaseBot):
    bot_key = "aggrH"
    bot_label = "Aggressive Heuristic Bot"

    def __init__(self, verbose: bool = False):
        super().__init__(name="AgHeBot", verbose=verbose)

    # Score penalty for using S&S Token. The lower the penalty the more aggressively the token will be used
    SCOUT_N_SHOW_TOKEN_PENALTY = 75 # TODO: Make interface attribute?


    def choose_flip(self, hand: list[Card], player_index: int, rng: random.Random) -> bool:
        """
        Based on computed total hand rank. True if hand quality after a flip is better than before the flip
        """
        hand_after_flip = flip_entire_hand(hand)

        hand_rank_before = compute_hand_rank(hand)
        hand_rank_after = compute_hand_rank(hand_after_flip)

        return hand_rank_after > hand_rank_before

    def select_move(self, state: GameState, moves: list[Move], rng: random.Random) -> Move:
        active_player = state.current_player

        # Partition moves by category
        show_moves = [m for m in moves if isinstance(m, ShowMove)]
        scout_moves = [m for m in moves if isinstance(m, ScoutMove)]
        scout_show_moves = [m for m in moves if isinstance(m, ScoutAndShowMove)]

        # Show aggressively if available
        if show_moves:
            strongest_move = sorted(show_moves, key=lambda move: move.candidate.rank)[-1]
            return strongest_move

        # Compare current hand rank score against prospective hand rank score
        # The score is weighted heuristically here
        current_hand_rank = compute_hand_rank(state.hands[active_player])
        current_hand_score = self._collapse_rank_to_score(current_hand_rank)

        # Scout Move search
        best_scout = None
        best_scout_score = None
        for move in scout_moves:
            next_state = apply_move(state, move)
            next_hand_score = self._collapse_rank_to_score(compute_hand_rank(next_state.hands[active_player]))
            move_score = next_hand_score - current_hand_score
            if best_scout is None or move_score > best_scout_score:
                best_scout = move
                best_scout_score = move_score

        # Scout&Show Move search
        best_scout_n_show = None
        best_scout_n_show_score = None
        for move in scout_show_moves:
            next_state = apply_move(state, move)

            # If a Scout&Show move would empty the hand, apply it immediately
            if not next_state.hands[active_player]:
                return move

            next_hand_score = self._collapse_rank_to_score(compute_hand_rank(next_state.hands[active_player]))
            show_score = self._collapse_rank_to_score(move.candidate.show.rank)

            # Calculate a score for the Scout&Show move
            move_score = show_score + (next_hand_score - current_hand_score) - self.SCOUT_N_SHOW_TOKEN_PENALTY
            if self.verbose:
                print(
                    f"--- AHBot Scout&Show Move evaluation ---\n"
                    f"Score: {move_score}\n"
                    f"Show Score: {show_score}\n"
                    f"Next Hand Score: {next_hand_score}\n"
                    f"Current Hand Score: {current_hand_score}\n"
                    f"Delta: {next_hand_score - current_hand_score}\n"
                    f"Token Penalty: {self.SCOUT_N_SHOW_TOKEN_PENALTY}"
                )

            if best_scout_n_show is None or move_score > best_scout_n_show_score:
                best_scout_n_show = move
                best_scout_n_show_score = move_score

        if best_scout_n_show is None:
            return best_scout

        if best_scout_n_show_score > best_scout_score:
            return best_scout_n_show
        return best_scout

    def _collapse_rank_to_score(self, hand_rank: tuple[int, int, int]) -> int:
        length, kind_rank, value_rank = hand_rank
        return length * 100 + kind_rank * 50 + value_rank