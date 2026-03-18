from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd
from tools.Logging import FlipRecord, GameResult, RoundResult, TurnRecord


@dataclass(frozen=True)
class ExportBundle:
    """Describe the two pickle files produced for one exported game."""

    directory: Path
    stem: str
    turns_file: Path
    flips_file: Path


def export_game_result(game_result: GameResult, output_dir: str | Path = "exports") -> ExportBundle:
    """Write the canonical turn and flip decision logs for one game."""
    export_time = datetime.now().astimezone()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    stem = build_export_stem(game_result, export_time)
    turns = build_turns_df(game_result, export_time)
    flips = build_flips_df(game_result, export_time)

    turns_file = output_path / f"{stem}_turns.pkl"
    flips_file = output_path / f"{stem}_flips.pkl"

    turns.to_pickle(turns_file)
    flips.to_pickle(flips_file)

    return ExportBundle(
        directory=output_path,
        stem=stem,
        turns_file=turns_file,
        flips_file=flips_file,
    )

def build_export_stem(game_result: GameResult, exported_at: datetime) -> str:
    """Build a readable filename stem with the reproducibility-relevant metadata."""
    seat_signature = "-".join(_slugify(seat_type) for seat_type in game_result.seat_types)
    timestamp = exported_at.strftime("%Y%m%dT%H%M%S")
    return (
        f"scoutbot_seed-{game_result.seed}"
        f"_players-{game_result.n_players}"
        f"_seats-{seat_signature}"
        f"_game-{game_result.game_id}"
        f"_ts-{timestamp}"
    )


def build_turns_df(game_result: GameResult, exported_at: datetime) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for round_result in game_result.rounds:
        for turn_record in round_result.turn_log:
            row = _round_base_row(game_result, round_result, exported_at)
            row.update(_flatten_turn_record_row(turn_record))
            rows.append(row)

    return pd.DataFrame(rows).set_index(["game_id", "round_num", "turn_index"]).sort_index()


def build_flips_df(game_result: GameResult, exported_at: datetime) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for round_result in game_result.rounds:
        for flip_index, flip_record in enumerate(round_result.flip_log):
            row = _round_base_row(game_result, round_result, exported_at)
            row.update(_flatten_flip_record_row(flip_record, flip_index))
            rows.append(row)

    return pd.DataFrame(rows).set_index(["game_id", "round_num", "flip_index"]).sort_index()


def _round_base_row(game_result: GameResult, round_result: RoundResult, exported_at: datetime) -> dict[str, Any]:
    """Shared game-level and round-level metadata for every decision row."""
    row = {
        "game_id": game_result.game_id,
        "round_num": round_result.round_num,
        "seed": game_result.seed,
        "n_players": game_result.n_players,
        "seat_types": list(game_result.seat_types),
        "seat_signature": "|".join(game_result.seat_types),
        "start_player": round_result.start_player,
        "end_reason": round_result.end_reason,
        "scores_in": list(round_result.scores_in),
        "scores_out": list(round_result.scores_out),
        "exported_at": exported_at.isoformat(),
    }
    row.update(_indexed_values("seat_type", game_result.seat_types))
    row.update(_indexed_values("score_in", round_result.scores_in))
    row.update(_indexed_values("score_out", round_result.scores_out))
    return row


def _flatten_turn_record_row(turn_record: TurnRecord) -> dict[str, Any]:
    """Flattens a TurnRecord while keeping the logged payloads intact."""
    row = {
        "turn_index": turn_record.turn_index,
        "player": turn_record.player,
        "player_type": turn_record.player_type,
        "state_before": turn_record.state_before,
        "move": turn_record.move,
        "scores_before": list(turn_record.scores_before),
        "scores_after": list(turn_record.scores_after),
        "hand_sizes_before": list(turn_record.hand_sizes_before),
        "hand_sizes_after": list(turn_record.hand_sizes_after),
        "table_rank_before": turn_record.table_rank_before,
        "table_rank_after": turn_record.table_rank_after,
    }
    row.update(_flatten_nested_dict("state_before", turn_record.state_before))
    row.update(_flatten_nested_dict("move", turn_record.move))
    # Keep both raw lists and numbered convenience columns for feature engineering.
    row.update(_indexed_values("scores_before", turn_record.scores_before))
    row.update(_indexed_values("scores_after", turn_record.scores_after))
    row.update(_indexed_values("hand_sizes_before", turn_record.hand_sizes_before))
    row.update(_indexed_values("hand_sizes_after", turn_record.hand_sizes_after))
    return row


def _flatten_flip_record_row(flip_record: FlipRecord, flip_index: int) -> dict[str, Any]:
    """Flattens a FlipRecord while preserving the hand snapshot."""
    row = {
        "flip_index": flip_index,
        "player": flip_record.player,
        "player_type": flip_record.player_type,
        "hand_before": list(flip_record.hand_before),
        "hand_size": len(flip_record.hand_before),
        "flipped": flip_record.flipped,
    }
    row.update(_indexed_values("hand_before_card", flip_record.hand_before))
    return row


def _indexed_values(prefix: str, values: list[Any]) -> dict[str, Any]:
    """Expands a list into numbered columns like `scores_0`."""
    return {f"{prefix}_{index}": value for index, value in enumerate(values)}


def _flatten_nested_dict(prefix: str, value: Any) -> dict[str, Any]:
    """Flattens nested dicts into one-level column names."""
    flattened: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, nested_value in value.items():
            child_prefix = f"{prefix}_{key}"
            if isinstance(nested_value, dict):
                flattened.update(_flatten_nested_dict(child_prefix, nested_value))
            else:
                flattened[child_prefix] = nested_value
    else:
        flattened[prefix] = value
    return flattened


def _slugify(value: str) -> str:
    """Converts a label into a simple filesystem-safe slug."""
    return "".join(
        char.lower() if char.isalnum() else "-"
        for char in value
    ).strip("-") or "unknown"
