"""Translates session events into log output in the side-panel"""

from tui.screens.game.GameSessionAdapter import SessionEvent
from tui.screens.game.widgets import GameLog


def log_session_events(logger: GameLog, events: list[SessionEvent], bots: list) -> None:
    """Writes the log lines for one batch of session events."""
    for event in events:
        # Pre-calculate the label for any event that has a 'player' index
        player_idx = event.data.get("player")
        label = _player_label(player_idx, bots) if player_idx is not None else ""

        if event.kind == "round_started":
            logger.log_round_start(
                event.data["round_num"],
                event.data["total_rounds"],
                event.data["n_players"]
            )

        elif event.kind == "flip_submitted":
            flipped = event.data["flipped"]
            action = "flipped" if flipped else "kept"
            logger.log_info(f"{label} {action} their hand.")

        elif event.kind == "move_submitted":
            logger.log_move(
                event.data["player"],
                event.data["move"],
                bot_list=bots,
                context=event.data.get("context")
            )

        elif event.kind == "round_finished":
            reason = (
                "No one could beat the show."
                if event.data["end_reason"] == "unbeaten_show_cycle"
                else "Someone emptied their hand."
            )

            logger.log_round_end(
                reason,
                event.data["scores_in"],
                event.data["scores_out"],
                round_num=event.data["round_num"],
                total_rounds=event.data["total_rounds"]
            )

        elif event.kind == "game_finished":
            scores = ", ".join(f"{_player_label(i, bots)}: {s}" for i, s in enumerate(event.data["scores_final"]))
            logger.log_phase("Game Over")
            logger.log_info(f"Final scores -> {scores}")

# TODO: extract and make helper, its also in summary builder now, other formatting helpers?? evaluate
def _player_label(index: int, bots: list) -> str:
    """Handles seat labeling."""
    is_human = bots[index] is None

    if not is_human:
        return f"P{index} (Bot)"

    human_count = bots.count(None)
    if human_count > 1:
        return f"P{index} (Human)"

    return "YOU"