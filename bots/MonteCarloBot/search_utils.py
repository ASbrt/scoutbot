import random
from dataclasses import replace
from bots.RandomBot import RandomBot
from engine.logic.helpers import any_empty_hand, unbeaten_show_cycle, apply_end_of_round_penalties
from engine.logic.legal_moves import apply_move, get_all_legal_moves
from engine.state.GameState import GameState


def simulate_round_from_state(state: GameState, bots: list, rng: random.Random) -> GameState:
    """
    Simulate the rest of the current round from an existing GameState until round end. Any human seat is treated as a
    random bot during simulation. The returned GameState includes final scores.
    """
    simulation_state = state
    ended_by_unbeaten_cycle = False

    while True:
        if any_empty_hand(simulation_state):
            break

        if unbeaten_show_cycle(simulation_state):
            ended_by_unbeaten_cycle = True
            break

        legal_moves = get_all_legal_moves(simulation_state)
        if not legal_moves:
            raise RuntimeError("No legal moves available during MCBot rollout.")

        player = simulation_state.current_player
        bot = bots[player]

        # Replace any human player with a bot for simulation
        if bot is None:
            bot = RandomBot()

        move = bot.select_move(simulation_state, legal_moves, rng)
        simulation_state = apply_move(simulation_state, move)

    final_scores = apply_end_of_round_penalties(simulation_state, unbeaten_show_cycle=ended_by_unbeaten_cycle)

    return replace(simulation_state, scores=list(final_scores))


def calculate_player_round_score_delta(initial_state: GameState, final_state: GameState, player: int) -> float:
    """
    Score delta between initial and final GameState for a player
    """
    return final_state.scores[player] - initial_state.scores[player]


def build_rollout_bots(n_players: int) -> list:
    """
    Builds rollout policies for all seats. For now its RandomBots
    """
    return [RandomBot() for _ in range(n_players)]