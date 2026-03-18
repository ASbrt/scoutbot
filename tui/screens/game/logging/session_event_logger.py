"""Translate session events into log output in the side-panel"""

from tui.screens.game.GameSessionAdapter import SessionEvent
from tui.screens.game.widgets import GameLog


def log_session_events(logger: GameLog, events: list[SessionEvent]) -> None:
    """Write the user-facing log lines for one batch of session events."""
    for event in events:
        if event.kind == "round_started":
            logger.log_round_start(
                event.data["round_num"],
                event.data["total_rounds"],
                event.data["n_players"],
            )

        elif event.kind == "flip_submitted":
            player = event.data["player"]
            flipped = event.data["flipped"]
            if event.data["is_bot"]:
                action = "flipped" if flipped else "kept"
                logger.log_info(f"P{player} (Bot) {action} their hand.")
            else:
                logger.log_info("You flipped your hand!" if flipped else "You kept your hand.")

        elif event.kind == "move_submitted":
            logger.log_move(
                event.data["player"],
                event.data["move"],
                is_bot=event.data["is_bot"],
                context=event.data.get("context"),
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
                total_rounds=event.data["total_rounds"],
            )

        elif event.kind == "game_finished":
            scores = ", ".join(f"P{i}: {score}" for i, score in enumerate(event.data["scores_final"]))
            logger.log_phase("Game Over")
            logger.log_info(f"Final scores -> {scores}")
