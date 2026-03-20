"""
First evaluation harness for bot performance. When running this file expect to wait for a while. The simple
Monte Carlo Bot has a few hundred possible moves to run through in the beginning of a game and then simulates a full game for each
of those starting moves. Combined with rollouts, the compute time explodes quickly.

Best to run this while doing something else unless it is for like 1 or 2 games. Or not at all for now.
"""

# TODO: turn this into an actual flexible tournament runner, then wire into TUI

import random
import time
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from bots.RandomBot import RandomBot
from bots.MonteCarloBot.MCBot import MCBot
from engine.logic.GameLoop import play_game


def run_game(game_id: int, seed: int, n_players: int, mc_rollouts: int) -> dict:
    """
    Runs one game and returns the result as a dictionary so it can be interpreted as a df row.

    Includes a timer for performance analysis given a number of rollouts.
    """
    rng = random.Random(seed)
    bots = [MCBot(n_rollouts=mc_rollouts)] + [RandomBot() for _ in range(n_players - 1)]

    start_time = time.perf_counter()
    result = play_game(game_id=game_id, seed=seed, bots=bots, rng=rng, n_players=n_players, log_turns=False, verbose=False)
    duration_sec = time.perf_counter() - start_time

    scores = list(result.scores_final)
    winner_score = max(scores)
    winner_seat = scores.index(winner_score)

    row = {
        "game_id": game_id,
        "seed": seed,
        "mc_rollouts": mc_rollouts,
        "duration_sec": duration_sec,
        "n_players": n_players,
        "winner_seat": winner_seat,
        "winner_bot": result.seat_types[winner_seat]
    }

    for i in range(n_players):
        row[f"seat_{i}_bot"] = result.seat_types[i]
        row[f"score_{i}"] = scores[i]

    return row


def run_tournament(n_games: int, n_players: int, mc_rollouts: int, seed_start: int) -> pd.DataFrame:
    rows = []

    for game_id in tqdm(range(n_games), desc="Running tournament"):
        seed = seed_start + game_id
        rows.append(run_game(game_id=game_id, seed=seed, n_players=n_players, mc_rollouts=mc_rollouts))

    return pd.DataFrame(rows)


def main():
    n_games = 100
    n_players = 4
    mc_rollouts = 10
    seed_start = 10000

    df = run_tournament(n_games=n_games, n_players=n_players, mc_rollouts=mc_rollouts, seed_start=seed_start)

    print(df.head())
    print("Average scores:")
    print("\nWin counts:")
    print(df["winner_bot"].value_counts())

    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / "exports" / "tournaments" / f"{n_games}_{n_players}_{mc_rollouts}_{seed_start}_tournament.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)
    print(f"\nSaved results to {output_path}")


if __name__ == "__main__":
    main()