"""Builds round-end and game-end summary modal content"""

from typing import Optional
from tools.data_export import ExportBundle
from tools.Logging import GameResult, RoundResult
from tui.screens.game.modals.SummaryModal import SummaryModal


def build_round_summary_modal(round_result: RoundResult, bots: list) -> SummaryModal:
    score_delta_lines = _format_score_delta(
        round_result.scores_in,
        round_result.scores_out,
        round_result.penalties,
        bots
    )

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


def _format_score_delta(scores_in: list[int], scores_out: list[int], penalties: list[int], bots: list) -> str:
    """Formats per-player score deltas and hand penalties."""
    lines = []
    # Zip all three lists together
    for index, (before, after, penalty) in enumerate(zip(scores_in, scores_out, penalties)):
        label = _player_label(index, bots)
        delta = after - before

        # Only show the penalty note if they actually lost points
        penalty_note = f" [Penalty: {penalty}]" if penalty < 0 else ""

        lines.append(f"{label:<8}: {before:>3} -> {after:>3} ({delta:+d}){penalty_note}")

    return "\n".join(lines)


def _format_score_lines(scores: list[int], bots: list) -> str:
    """Format a per-player scoreboard for summary modals."""
    return "\n".join(f"{_player_label(index, bots)}: {score}" for index, score in enumerate(scores))


def _player_label(index: int, bots: list) -> str:
    """Handles seat labeling."""
    is_human = bots[index] is None

    if not is_human:
        return f"P{index} (Bot)"

    human_count = bots.count(None)
    if human_count > 1:
        return f"P{index} (Human)"

    return "YOU"
