import random
from typing import Optional

from GameLoop import play_round # your play_round
from Logging import RoundResult
from helpers import any_empty_hand  # optional

# If you want to show move strings, reuse whatever you have:
# from pretty_print import move_to_str


def print_round_summary(rr: RoundResult) -> None:
    """
    Human-readable round summary.
    Assumes RoundResult has: round_num, start_player, end_reason, scores_in, scores_out, turn_log
    """
    print("\n" + "=" * 60)
    print(f"ROUND {rr.round_num} finished")
    print(f"Start player: P{rr.start_player}")
    print(f"End reason:   {rr.end_reason}")
    print(f"Turns played: {len(rr.turn_log)}")

    # Score deltas
    deltas = [out - inn for out, inn in zip(rr.scores_out, rr.scores_in)]
    delta_str = " ".join([f"P{i}:{d:+d}" for i, d in enumerate(deltas)])
    print(f"Score Δ:      {delta_str}")

    print(f"Scores in:    {rr.scores_in}")
    print(f"Scores out:   {rr.scores_out}")
    print("=" * 60)


def play_game_cli(
    bots: list,
    n_players: int,
    seed: int = 0,
    n_rounds: Optional[int] = None,
    start_player_mode: str = "random_then_rotate",  # "random_each" | "random_then_rotate" | "rotate"
    log_turns: bool = True,
    verbose_turns: bool = False,
) -> list[int]:
    """
    CLI wrapper around play_round.

    start_player_mode:
      - "random_each": start player random each round
      - "rotate": start player rotates starting at 0
      - "random_then_rotate": choose random start player in round 1, then rotate thereafter
    """
    if len(bots) != n_players:
        raise ValueError(f"Need {n_players} bots, got {len(bots)}")

    if n_rounds is None:
        n_rounds = n_players  # your current rule: each player starts once

    rng = random.Random(seed)
    scores = [0] * n_players

    start_player: Optional[int]
    if start_player_mode == "random_each":
        start_player = None
    elif start_player_mode == "rotate":
        start_player = 0
    elif start_player_mode == "random_then_rotate":
        start_player = None
    else:
        raise ValueError("Invalid start_player_mode")

    for r in range(1, n_rounds + 1):
        print("\n" + "#" * 60)
        print(f"### START ROUND {r}")
        print(f"Current total scores: {scores}")
        print("#" * 60)

        rr = play_round(
            bots=bots,
            rng=rng,
            n_players=n_players,
            round_num=r,
            scores_in=scores,
            start_player=start_player,
            log_turns=log_turns,
            verbose=verbose_turns,  # uses your per-turn printer
        )

        print_round_summary(rr)
        scores = rr.scores_out

        # Start player logic
        if start_player_mode == "random_each":
            start_player = None
        elif start_player_mode == "rotate":
            start_player = (start_player + 1) % n_players
        else:  # random_then_rotate
            if start_player is None:
                start_player = rr.start_player
            start_player = (start_player + 1) % n_players

    print("\n" + "*" * 60)
    print("GAME OVER")
    print(f"Final scores: {scores}")
    print("*" * 60)

    return scores

if __name__ == "__main__":
    from HumanPlayer import HumanBot
    from Bots import RandomBot  # your random bot

    bots = [HumanBot("You"), RandomBot(), RandomBot()]
    play_game_cli(bots=bots, n_players=3, seed=1, verbose_turns=True)
