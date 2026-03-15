from dataclasses import dataclass
from typing import Optional
from engine.state.GameState import GameState, Move, ShowMove, ScoutMove, ScoutAndShowMove
from engine.logic.helpers import get_active_values

@dataclass
class TurnRecord:
    round_num: int
    turn_index: int
    player: int
    move: Move
    scores_before: list[int]
    scores_after: list[int]
    hand_sizes_before: list[int]
    hand_sizes_after: list[int]
    table_rank_before: Optional[tuple[int, int, int]]
    table_rank_after: Optional[tuple[int, int, int]]


@dataclass
class RoundResult:
    round_num: int
    start_player: int
    end_reason: str  # "empty_hand" | "unbeaten_show_cycle"
    scores_in: list[int]
    scores_out: list[int]
    turn_log: list[TurnRecord]


@dataclass
class GameResult:
    n_players: int
    n_rounds: int
    scores_final: list[int]
    rounds: list[RoundResult]


def table_to_str(state: GameState) -> str:
    if state.table is None:
        return "Table: (empty)"
    vals = [c.active for c in state.table.cards]
    return f"Table: P{state.table.played_by} {state.table.kind.upper()} {vals} rank={state.table.rank}"


def move_to_str(move: Move) -> str:
    if isinstance(move, ShowMove):
        c = move.candidate
        return f"SHOW {c.kind.upper()} values={c.values} (start={c.start}, len={c.length})"
    if isinstance(move, ScoutMove):
        c = move.candidate
        end = "LEFT" if c.table_index == 0 else "RIGHT"
        flip = "flip" if c.flip else "keep"
        return f"SCOUT take={end} insert@{c.hand_insert_index} {flip}"
    if isinstance(move, ScoutAndShowMove):
        s = move.candidate.scout
        sh = move.candidate.show
        end = "LEFT" if s.table_index == 0 else "RIGHT"
        flip = "flip" if s.flip else "keep"
        return (
            f"SCOUT&SHOW take={end} insert@{s.hand_insert_index} {flip} -> "
            f"SHOW {sh.kind.upper()} values={sh.values} (start={sh.start}, len={sh.length})"
        )
    return str(move)


def score_delta(before: list[int], after: list[int]) -> list[int]:
    return [a - b for a, b in zip(after, before)]


def print_turn(round_num: int, turn_index: int, player: int, state_before: GameState, move: Move, state_after: GameState,
    show_active_hand: bool = False) -> None:

    print(f"\nR{round_num} · Turn {turn_index} · Player P{player}")
    print("  " + table_to_str(state_before))
    if show_active_hand:
        hand_vals = get_active_values(state_before.hands[player])
        print(f"  Hand P{player}: {hand_vals}")

    print(f"  Action: {move_to_str(move)}")

    # Score change
    d = score_delta(state_before.scores, state_after.scores)
    d_str = " ".join([f"P{i}:{d[i]:+d}" for i in range(len(d)) if d[i] != 0]) or "no change"
    print(f"  Score Δ: {d_str}")
    print(f"  Scores:  {state_before.scores} -> {state_after.scores}")

    # Table after
    print("  " + table_to_str(state_after))