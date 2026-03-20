import random
from engine.logic.legal_moves import apply_move
from engine.state.CardCore import Card
from engine.state.GameState import GameState, Move
from .search_utils import simulate_round_from_state, calculate_player_round_score_delta, build_rollout_bots
from ..BaseBot import BaseBot

# TODO: prune move options (With Heuristics?). Simulating a game with MCBot takes way to much time
# TODO: implement flip search --> computationally expensive though when simulating like this...

class MCBot(BaseBot):
    """
    For each legal move, simulates the rest of the round multiple times and
    chooses the move with the best average outcome for the current player (biggest score delta)
    """
    bot_key = "mc1"
    bot_label = "Simple Monte Carlo Bot"

    def __init__(self, n_rollouts: int = 50, verbose: bool = False):
        super().__init__(name="MCBot", verbose=verbose)
        self.n_rollouts = n_rollouts

    def choose_flip(self, hand: list[Card], player_index: int, rng: random.Random) -> bool:
        """
        Flip choice is random for now, focusing on search
        """
        return rng.random() < 0.5

    def select_move(self, state: GameState, moves: list[Move], rng: random.Random) -> Move:
        """
        Evaluate each legal move with Monte Carlo rollout and return the best one. This version operates under perfect information,
        so it is cheating a bit.
        """
        if not moves:
            raise RuntimeError("MCBot received no legal moves.")

        rollout_bots = build_rollout_bots(len(state.hands))

        best_move = None
        best_value_so_far = float("-inf")

        if self.verbose:
            print(f"MCBot is evaluating {len(moves)} moves with {self.n_rollouts} rollouts each")

        for move in moves:
            total_value = 0

            # Apply each move n_rollouts times, simulate the rest of the round and return the avg score delta.
            # Since move choice in the simulation is non-deterministic and states are branching multiple rollouts make sense
            for _ in range(self.n_rollouts):
                state_after_move = apply_move(state, move)
                final_state = simulate_round_from_state(state_after_move, rollout_bots, rng)
                total_value += calculate_player_round_score_delta(
                    initial_state=state,
                    final_state=final_state,
                    player=state.current_player,
                )

            avg_move_value = total_value / self.n_rollouts

            # Replace best move if the current avg beats the best value so far
            if avg_move_value > best_value_so_far:
                best_value_so_far = avg_move_value
                best_move = move

        return best_move