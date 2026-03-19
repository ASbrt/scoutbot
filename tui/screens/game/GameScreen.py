import random
from typing import Optional
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from bots.RandomBot import RandomBot
from tools.data_export import ExportBundle, export_game_result
from tui.screens.game.rendering.GameRenderer import GameRenderer
from .utils import generate_game_id
from .GameSessionAdapter import GameSession, SessionEvent
from .modals.FlipScreen import FlipScreen
from .modals.summary_builder import build_game_summary_modal, build_round_summary_modal
from .userInput.TurnInteractionController import TurnInteractionController
from .userInput.HumanInputUIState import TurnInputState
from .logging.session_event_logger import log_session_events
from .widgets import GameLog, StateOverview


class GameScreen(Screen):
    """
    Top-level coordinator for the ScoutBot gameplay screen. This screen owns the Textual layout, the session lifecycle
    and the modals. Rendering is delegated to GamePresenter, and human move-building is delegated
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

    # To stop key-presses like Enter to go back to lobby screen
    can_focus = True

    def __init__(self, config):
        """Initialize all components used for one visible game screen."""
        super().__init__()
        self.config = config
        self.rng = random.Random(config.seed)
        # A `None` seat is interpreted as a human player, bot instances occupy the remaining seats.
        self.bots = [RandomBot() if seat_type == "random" else None for seat_type in config.seat_types]
        self.session: Optional[GameSession] = None
        self.input_state = TurnInputState()
        self.renderer = GameRenderer(self)
        self.turn_interaction = TurnInteractionController(self)
        self._flip_modal_open = False
        self._summary_modal_open = False
        self._export_bundle: Optional[ExportBundle] = None

    def compose(self) -> ComposeResult:
        """Build the static gameplay layout; live data is filled in later."""
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
                yield StateOverview(id="player_summary")
                yield Static("Round info...", id="resource_info")

            with Vertical(id="log_panel"):
                yield Static("GAME LOG", classes="header")
                yield GameLog(id="game_log")

        yield Footer()

    def on_mount(self) -> None:
        """Disable button focus and start the session after the first refresh."""
        for btn_id in ["#exit_game", "#btn_show", "#btn_scout", "#btn_scout_show"]:
            self.query_one(btn_id, Button).can_focus = False

        self.focus()
        self.call_after_refresh(self.start_game)

    @property
    def logger(self) -> GameLog:
        """Convenience accessor for the side-panel log widget."""
        return self.query_one("#game_log", GameLog)

    def start_game(self) -> None:
        """Create the controller-backed session and advance to the first human stop."""
        self.logger.log_info("Welcome to ScoutBot!")
        self.session = GameSession(
            seed=self.config.seed,
            bots=self.bots,
            rng=self.rng,
            n_players=self.config.n_players,
            game_id=generate_game_id(),
        )
        self._handle_session_events(self.session.start())
        self._advance_session()

    def _advance_session(self) -> None:
        """Advance controllers until the UI must stop for human input or game over."""
        if self.session is None:
            return

        self._handle_session_events(self.session.advance_until_human_or_end())
        self.renderer.refresh()
        self._export_game_if_needed()
        if self._open_summary_modal_if_needed():
            return
        self._open_flip_modal_if_needed()

    def _open_flip_modal_if_needed(self) -> None:
        """Open the flip modal exactly when the session is waiting on a human flip."""
        if self.session is None or self._flip_modal_open or self._summary_modal_open or not self.session.waiting_for_human_flip():
            return

        round_controller = self.session.round_controller
        self._flip_modal_open = True
        self.logger.log_phase("Hand Flip Decision")
        self.app.push_screen(FlipScreen(round_controller.get_flip_hand()), self.handle_flip_result)

    def handle_flip_result(self, flipped: bool) -> None:
        """Receive the modal result, submit it, and resume session advancement."""
        self._flip_modal_open = False
        if self.session is None:
            return

        self._handle_session_events(self.session.submit_flip(flipped))
        self.input_state.reset()
        self._advance_session()

    def _open_summary_modal_if_needed(self) -> bool:
        """Open a round-end or game-end summary modal if one is pending."""
        if self._summary_modal_open:
            return True
        if self.session is None:
            return False

        if self.session.is_game_over():
            final_result = self.session.final_result()
            if final_result is None:
                return False
            self._summary_modal_open = True
            self.app.push_screen(
                build_game_summary_modal(
                    final_result,
                    self.bots,
                    self._export_bundle,
                ),
                self._handle_summary_modal_closed,
            )
            return True

        if self.session.has_pending_round_summary():
            round_result = self.session.latest_round_result()
            if round_result is None:
                return False
            self._summary_modal_open = True
            self.app.push_screen(
                build_round_summary_modal(round_result, self.bots),
                self._handle_summary_modal_closed,
            )
            return True

        return False

    def _handle_summary_modal_closed(self, _result=None) -> None:
        """Resume play after round summaries or leave the screen after game end."""
        self._summary_modal_open = False
        if self.session is None:
            return

        if self.session.is_game_over():
            self.app.pop_screen()
            return

        self._advance_session()

    def _export_game_if_needed(self) -> None:
        """Persist the finished game once, right after the final result exists."""
        if self.session is None or not self.session.is_game_over() or self._export_bundle is not None:
            return

        result = self.session.final_result()
        if result is None:
            return

        try:
            # Export after `presenter.refresh()` so the user still sees the final
            # state even if export ever throws an unexpected exception.
            self._export_bundle = export_game_result(result)
            self.logger.log_info(
                f"Exported game data to {self._export_bundle.directory} "
                f"({self._export_bundle.turns_file.name}, {self._export_bundle.flips_file.name})"
            )
        except Exception as exc:
            self.logger.log_error(f"Automatic export failed: {exc}")

    def _submit_human_move(self, move) -> None:
        """Session submission stays on the screen so orchestration remains centralized."""
        if self.session is None:
            return

        self._handle_session_events(self.session.submit_move(move))
        self.input_state.reset()
        self._advance_session()

    def _handle_session_events(self, events: list[SessionEvent]) -> None:
        """Apply the small screen-side reactions around one event batch."""
        if any(event.kind == "round_started" for event in events):
            self.input_state.reset()
        log_session_events(self.logger, events)

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
