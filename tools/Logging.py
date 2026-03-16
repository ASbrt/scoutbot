from dataclasses import dataclass
from typing import Optional

@dataclass
class FlipRecord:
    player: int
    player_type: str
    hand_before: list[dict]
    flipped: bool


@dataclass
class TurnRecord:
    turn_index: int
    player: int
    player_type: str
    state_before: dict
    move: dict
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
    end_reason: str
    scores_in: list[int]
    scores_out: list[int]
    flip_log: list[FlipRecord]
    turn_log: list[TurnRecord]


@dataclass
class GameResult:
    game_id: int
    seed: int
    n_players: int
    seat_types: list[str]
    n_rounds: int
    scores_final: list[int]
    rounds: list[RoundResult]
