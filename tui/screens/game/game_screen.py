import random
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from players.Bots import RandomBot

from .flip_screen import FlipScreen
from .game_presenter import GamePresenter
from .game_session import GameSession, SessionEvent
from .summary_modal import SummaryModal
from .turn_input import TurnInputState
from .turn_interaction import TurnInteractionController
from .widgets import GameLog, PlayerSummary


class GameScreen(Screen):
    """
    Top-level coordinator for the ScoutBot gameplay screen.

    This screen owns the Textual layout, the session lifecycle, and the flip modal.
    Rendering is delegated to GamePresenter, and human move-building is delegated
    to TurnInteractionController.
    """

    BINDINGS = [
        Binding("left", "cursor_left", "Cursor Left", show=False),
        Binding("right", "cursor_right", "Cursor Right", show=False),
        Binding("space", "toggle_selection", "Select", show=False),
        Binding("enter", "confirm_action", "Confirm", show=False),
        Binding("escape", "cancel_action", "Cancel", show=False),
        Binding("s", "choose_show", "Show", show=False),
        Binding("c", "choose_scout", "Scout", show=False),
        Binding("a", "choose_sas", "Scout & Show", show=False),
    ]

    can_focus = True

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.rng = random.Random(config.seed)
        self.bots = [RandomBot() if seat_type == "random" else None for seat_type in config.seat_types]
        self.session: Optional[GameSession] = None
        self.turn_input = TurnInputState()
        self.presenter = GamePresenter(self)
        self.turn_interaction = TurnInteractionController(self)
        self._flip_modal_open = False
        self._summary_modal_open = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="game_top_bar"):
            yield Static("ScoutBot - Game View", id="game_title")
            yield Static("Round: 1", id="game_status")
            yield Button("Back to Lobby", id="exit_game", variant="error")

        with Horizontal(id="game_main"):
            with Vertical(id="play_area"):
                yield Static("TABLE", classes="header")
                yield Static("(Table)", id="table_area")
                yield Static("YOUR HAND", classes="header")
                yield Static("(Hand)", id="hand_area")
                yield Static(
                    "Use Arrow Keys to move cursor, Space to select, Enter to confirm.",
                    id="interaction_hint",
                )

                with Horizontal(id="game_controls"):
                    yield Button("Show", id="btn_show", variant="primary")
                    yield Button("Scout", id="btn_scout")
                    yield Button("Scout & Show", id="btn_scout_show")

            with Vertical(id="side_panel"):
                yield Static("OVERVIEW", classes="header")
                yield PlayerSummary(id="player_summary")
                yield Static("Round info...", id="resource_info")

            with Vertical(id="log_panel"):
                yield Static("GAME LOG", classes="header")
                yield GameLog(id="game_log")

        yield Footer()

    def on_mount(self) -> None:
        for btn_id in ["#exit_game", "#btn_show", "#btn_scout", "#btn_scout_show"]:
            self.query_one(btn_id, Button).can_focus = False

        self.focus()
        self.call_after_refresh(self.start_game)

    @property
    def logger(self) -> GameLog:
        return self.query_one("#game_log", GameLog)

    def start_game(self) -> None:
        """Create the controller-backed session and advance to the first human stop."""
        self.logger.log_info("Welcome to ScoutBot!")
        self.session = GameSession(
            seed=self.config.seed,
            bots=self.bots,
            rng=self.rng,
            n_players=self.config.n_players,
            game_id=self.config.seed,
        )
        self._log_events(self.session.start())
        self._advance_session()

    def _advance_session(self) -> None:
        """Advance controllers until the UI must stop for human input or game over."""
        if self.session is None:
            return

        self._log_events(self.session.advance_until_human_or_end())
        self.presenter.refresh()
        if self._open_summary_modal_if_needed():
            return
        self._open_flip_modal_if_needed()

    def _open_flip_modal_if_needed(self) -> None:
        if self.session is None or self._flip_modal_open or self._summary_modal_open or not self.session.waiting_for_human_flip():
            return

        round_controller = self.session.round_controller
        self._flip_modal_open = True
        self.logger.log_phase("Hand Flip Decision")
        self.app.push_screen(FlipScreen(round_controller.get_flip_hand()), self.handle_flip_result)

    def handle_flip_result(self, flipped: bool) -> None:
        self._flip_modal_open = False
        if self.session is None:
            return

        self._log_events(self.session.submit_flip(flipped))
        self.turn_input.reset()
        self._advance_session()

    def _open_summary_modal_if_needed(self) -> bool:
        """Open a round-end or game-end summary modal if one is pending."""
        if self._summary_modal_open:
            return True
        if self.session is None:
            return False

        if self.session.is_game_over():
            self._summary_modal_open = True
            self.app.push_screen(self._build_game_end_modal(), self._handle_summary_modal_closed)
            return True

        round_result = self.session.game_controller.round_results[-1] if self.session.game_controller.round_results else None
        if round_result is not None and self.session.round_controller is None:
            self._summary_modal_open = True
            self.app.push_screen(self._build_round_end_modal(round_result), self._handle_summary_modal_closed)
            return True

        return False

    def _handle_summary_modal_closed(self, _result=None) -> None:
        self._summary_modal_open = False
        if self.session is None:
            return

        if self.session.is_game_over():
            self.app.pop_screen()
            return

        self._advance_session()

    def _build_round_end_modal(self, round_result) -> SummaryModal:
        delta_lines = self._format_score_delta_lines(round_result.scores_in, round_result.scores_out)
        score_lines = self._format_score_lines(round_result.scores_out)
        reason = "No one could beat the show." if round_result.end_reason == "unbeaten_show_cycle" else "Someone emptied their hand."
        body = (
            f"Reason: {reason}\n\n"
            f"Penalty / score delta:\n{delta_lines}\n\n"
            f"Scores after round:\n{score_lines}"
        )
        return SummaryModal(
            title=f"Round {round_result.round_num}/{self.config.n_players} Complete",
            body=body,
            button_label="Continue",
        )

    def _build_game_end_modal(self) -> SummaryModal:
        result = self.session.get_final_result()
        score_lines = self._format_score_lines(result.scores_final)
        highest_score = max(result.scores_final)
        winners = [self._player_label(index) for index, score in enumerate(result.scores_final) if score == highest_score]
        winner_text = ", ".join(winners)
        body = (
            f"Final scores:\n{score_lines}\n\n"
            f"Winner{'s' if len(winners) > 1 else ''}: {winner_text}"
        )
        return SummaryModal(
            title="Game Complete",
            body=body,
            button_label="Back to Lobby",
        )

    def _format_score_delta_lines(self, scores_in: list[int], scores_out: list[int]) -> str:
        lines = []
        for index, (before, after) in enumerate(zip(scores_in, scores_out)):
            delta = after - before
            lines.append(f"{self._player_label(index)}: {before} -> {after} ({delta:+d})")
        return "\n".join(lines)

    def _format_score_lines(self, scores: list[int]) -> str:
        return "\n".join(f"{self._player_label(index)}: {score}" for index, score in enumerate(scores))

    def _player_label(self, index: int) -> str:
        return "YOU" if self.bots[index] is None else f"P{index} (Bot)"

    def _submit_human_move(self, move) -> None:
        """Session submission stays on the screen so orchestration remains centralized."""
        if self.session is None:
            return

        self._log_events(self.session.submit_move(move))
        self.turn_input.reset()
        self._advance_session()

    def _log_events(self, events: list[SessionEvent]) -> None:
        """Translate session events into user-facing log lines."""
        for event in events:
            if event.kind == "round_started":
                self.turn_input.reset()
                self.logger.log_round_start(
                    event.data["round_num"],
                    event.data["total_rounds"],
                    event.data["n_players"],
                )
            elif event.kind == "flip_submitted":
                player = event.data["player"]
                flipped = event.data["flipped"]
                if event.data["is_bot"]:
                    action = "flipped" if flipped else "kept"
                    self.logger.log_info(f"P{player} (Bot) {action} their hand.")
                else:
                    self.logger.log_info("You flipped your hand!" if flipped else "You kept your hand.")
            elif event.kind == "move_submitted":
                self.logger.log_move(
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
                self.logger.log_round_end(
                    reason,
                    event.data["scores_in"],
                    event.data["scores_out"],
                    round_num=event.data["round_num"],
                    total_rounds=event.data["total_rounds"],
                )
            elif event.kind == "game_finished":
                scores = ", ".join(f"P{i}: {score}" for i, score in enumerate(event.data["scores_final"]))
                self.logger.log_phase("Game Over")
                self.logger.log_info(f"Final scores -> {scores}")

    def action_choose_show(self) -> None:
        self.turn_interaction.choose_show()

    def action_choose_scout(self) -> None:
        self.turn_interaction.choose_scout()

    def action_choose_sas(self) -> None:
        self.turn_interaction.choose_scout_and_show()

    def action_cursor_left(self) -> None:
        self.turn_interaction.cursor_left()

    def action_cursor_right(self) -> None:
        self.turn_interaction.cursor_right()

    def action_toggle_selection(self) -> None:
        self.turn_interaction.toggle_selection()

    def action_confirm_action(self) -> None:
        self.turn_interaction.confirm_action()

    def action_cancel_action(self) -> None:
        self.turn_interaction.cancel_action()

    def on_key(self, event) -> None:
        if self.turn_interaction.handle_orientation_key(event.key.lower()):
            return

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "exit_game":
            self.app.pop_screen()
        elif event.button.id == "btn_show":
            self.turn_interaction.choose_show()
        elif event.button.id == "btn_scout":
            self.turn_interaction.choose_scout()
        elif event.button.id == "btn_scout_show":
            self.turn_interaction.choose_scout_and_show()
