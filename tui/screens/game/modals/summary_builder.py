"""Build round-end and game-end summary modal content for GameScreen."""

from typing import Optional

from tools.data_export import ExportBundle
from tools.Logging import GameResult, RoundResult

from tui.screens.game.modals.SummaryModal import SummaryModal


def build_round_summary_modal(round_result: RoundResult, bots: list) -> SummaryModal:
    """Create the round-end summary modal from a finalized RoundResult."""
    score_delta_lines = _format_score_delta_lines(round_result.scores_in, round_result.scores_out, bots)
    score_lines = _format_score_lines(round_result.scores_out, bots)
    reason = (
        "No one could beat the show."
        if round_result.end_reason == "unbeaten_show_cycle"
        else "Someone emptied their hand."
    )
    body = (
        f"Reason: {reason}\n\n"
        f"Penalty / score delta:\n{score_delta_lines}\n\n"
        f"Scores after round:\n{score_lines}"
    )
    return SummaryModal(
        title=f"Round {round_result.round_num}/{len(bots)} Complete",
        body=body,
        button_label="Continue",
    )


def build_game_summary_modal(result: GameResult, bots: list, export_bundle: Optional[ExportBundle]) -> SummaryModal:
    """Create the game-end summary modal from the final GameResult."""
    score_lines = _format_score_lines(result.scores_final, bots)
    highest_score = max(result.scores_final)
    winner_labels = [
        _player_label(index, bots)
        for index, score in enumerate(result.scores_final)
        if score == highest_score
    ]
    export_note = ""
    if export_bundle is not None:
        export_note = (
            f"\n\nExported datasets:\n"
            f"{export_bundle.turns_file.name}\n"
            f"{export_bundle.flips_file.name}\n"
            f"in {export_bundle.directory}"
        )

    body = (
        f"Final scores:\n{score_lines}\n\n"
        f"Winner{'s' if len(winner_labels) > 1 else ''}: {', '.join(winner_labels)}"
        f"{export_note}"
    )
    return SummaryModal(
        title="Game Complete",
        body=body,
        button_label="Back to Lobby",
    )


def _format_score_delta_lines(scores_in: list[int], scores_out: list[int], bots: list) -> str:
    """Format per-player score deltas for the round-end modal."""
    lines = []
    for index, (before, after) in enumerate(zip(scores_in, scores_out)):
        delta = after - before
        lines.append(f"{_player_label(index, bots)}: {before} -> {after} ({delta:+d})")
    return "\n".join(lines)


def _format_score_lines(scores: list[int], bots: list) -> str:
    """Format a per-player scoreboard for summary modals."""
    return "\n".join(f"{_player_label(index, bots)}: {score}" for index, score in enumerate(scores))


def _player_label(index: int, bots: list) -> str:
    """Return the same seat labels used elsewhere in the gameplay TUI."""
    return "YOU" if bots[index] is None else f"P{index} (Bot)"
