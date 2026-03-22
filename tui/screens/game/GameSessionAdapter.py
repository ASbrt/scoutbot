"""An adapter for the game engine, needed for human interactivity with the TUI"""

import random
from dataclasses import dataclass, field
from typing import Optional
from engine.controllers.GameController import GameController
from engine.controllers.RoundController import RoundController, RoundStage
from engine.state.GameState import GameState, Move
from tools.Logging import GameResult, RoundResult
from tui.screens.game.logging.build_move_details import build_move_details


@dataclass(frozen=True)
class SessionEvent:
    """
    Shape of the events emitted while the session advances. GameSession converts controller-side progress into small event objects so
    GameScreen can log and render without needing to inspect controller internals.
    """

    kind: str
    # To avoid shallow freezing problems, i.e. shared state over multiple instances
    data: dict = field(default_factory=dict)


class GameSession:
    """Handles game and round progression for the TUI, stops when human input is needed."""

    def __init__(self, *, seed: int, bots: list, rng: random.Random, n_players: int, game_id: int = 0,
                 log_turns: bool = True) -> None:
        # GameSession owns one game controller and exposes a view of its progression
        self.game_controller = GameController(
            game_id=game_id,
            seed=seed,
            bots=bots,
            rng=rng,
            n_players=n_players,
            log_turns=log_turns,
        )
        self._last_visible_state: Optional[GameState] = None
        self.final_result: Optional[GameResult] = None

    @property
    def round_controller(self) -> Optional[RoundController]:
        """Exposes the currently active round controller, if present."""
        return self.game_controller.current_round

    @property
    def display_state(self) -> Optional[GameState]:
        """
        Returns the latest state the TUI should render. Between rounds or after game end we keep the last visible state
        around so the screen does not suddenly go blank before summary modals appear.
        """
        round_controller = self.round_controller
        if round_controller is not None and round_controller.state is not None:
            return round_controller.state
        return self._last_visible_state

    # -------------- Main advancement functions

    def start(self) -> list[SessionEvent]:
        """Start the first round and return the initial session events."""
        if self.round_controller is not None or self.final_result is not None:
            raise RuntimeError("GameSession has already been started")

        round_controller = self.game_controller.start_next_round()
        return [self._build_round_started_event(round_controller)]

    def advance_until_human_or_end(self) -> list[SessionEvent]:
        """
        Keeps advancing controllers until the UI needs to step in again. Builds a list of events
        """
        events: list[SessionEvent] = []

        while True:
            round_controller = self.round_controller

            if round_controller is None:
                # Either the game has not started its next round yet, or the previous round was just finalized
                # and we need to move at the game level
                if not self._advance_game_level(events):
                    break
                continue

            if round_controller.stage == RoundStage.FLIP:
                # Human stops are the only time we hand control back to the TUI
                if round_controller.stage == RoundStage.FLIP and not round_controller.current_actor_is_bot():
                    break
                self._advance_flip_stage(round_controller, events)
                continue

            if round_controller.stage == RoundStage.TURNS:
                # Break for human turns
                if round_controller.stage == RoundStage.TURNS and not round_controller.current_actor_is_bot():
                    break
                self._advance_turn_stage(round_controller, events)
                continue

            if round_controller.stage == RoundStage.FINISHED:
                self._advance_finished_round(round_controller, events)
                break

            raise RuntimeError(f"Unexpected round stage: {round_controller.stage}")

        return events

    # ------------ Submitting moves

    def submit_flip_choice(self, flipped: bool) -> list[SessionEvent]:
        """Submit the current human flip choice"""

        round_controller = self.round_controller
        if round_controller is None:
            raise RuntimeError("No active round controller")

        if round_controller.stage != RoundStage.FLIP:
            raise RuntimeError("submit_flip is only valid during flip phase")
        if round_controller.current_actor_is_bot():
            raise RuntimeError("submit_flip cannot be used for a bot actor")

        player = round_controller.current_flip_player()
        round_controller.submit_flip_decision(flipped)
        return [
            SessionEvent(
                "flip_submitted",
                {
                    "player": player,
                    "flipped": flipped,
                    "is_bot": False,
                },
            )
        ]

    def submit_move_choice(self, move: Move) -> list[SessionEvent]:
        """Submit one complete human move object to the controller."""

        round_controller = self.round_controller
        if round_controller is None:
            raise RuntimeError("No active round controller")

        if round_controller.stage != RoundStage.TURNS or round_controller.state is None:
            raise RuntimeError("submit_move is only valid during turn phase")
        if round_controller.current_actor_is_bot():
            raise RuntimeError("submit_move cannot be used for a bot actor")

        state_before = round_controller.state
        player = round_controller.current_turn_player()
        # Human moves go through the exact same controller method bots use, so they
        # are logged and validated by the same code path.
        round_controller.apply_selected_move(move)
        self._last_visible_state = round_controller.state
        return [
            self._build_move_event(player, move, is_bot=False, state_before=state_before, state_after=round_controller.state)
        ]

    # -------------- When to wait checks

    def waiting_for_human_flip(self) -> bool:
        """Tells the screen whether a human flip modal should be opened now."""
        round_controller = self.round_controller
        return (
                round_controller is not None and
                round_controller.stage == RoundStage.FLIP and
                not round_controller.current_actor_is_bot()
        )

    def waiting_for_human_turn(self) -> bool:
        """Tells the screen whether keyboard turn input should be active now."""
        round_controller = self.round_controller
        return (
                round_controller is not None and
                round_controller.stage == RoundStage.TURNS and
                not round_controller.current_actor_is_bot()
        )

    # -------------- Screen utilities

    def latest_round_result(self) -> Optional[RoundResult]:
        """Return the most recently finalized round result, if one exists."""
        if not self.game_controller.round_results:
            return None
        return self.game_controller.round_results[-1]

    def has_pending_round_summary(self) -> bool:
        """Tells the screen whether a round-end summary should be shown now."""
        return self.latest_round_result() is not None and self.round_controller is None and not self.is_game_over()

    def is_game_over(self) -> bool:
        """Returns whether the final GameResult has already been built. Bit nicer to read in GameScreen"""
        return self.final_result is not None

    # ---------------- Advancement helpers

    def _advance_game_level(self, events: list[SessionEvent]) -> bool:
        """Handles either starting the next round or finishing the full game."""
        if self.game_controller.is_finished:
            if self.final_result is None:
                # The final GameResult is only built once, after all rounds have
                # already been finalized back into GameController.
                self.final_result = self.game_controller.build_result()
                events.append(
                    SessionEvent("game_finished", {"scores_final": list(self.final_result.scores_final)})
                )
            return False

        round_controller = self.game_controller.start_next_round()
        events.append(self._build_round_started_event(round_controller))
        return True

    def _advance_flip_stage(self, round_controller: RoundController, events: list[SessionEvent]) -> None:
        """Resolve exactly one bot flip step."""
        player = round_controller.current_flip_player()
        flipped = round_controller.run_bot_flip_step()
        events.append(
            SessionEvent(
                "flip_submitted",
                {"player": player, "flipped": flipped, "is_bot": True},
            )
        )

    def _advance_turn_stage(self, round_controller: RoundController, events: list[SessionEvent]) -> None:
        """Resolve exactly one bot move step."""
        if round_controller.state is None:
            raise RuntimeError("RoundController is in TURNS stage without state")

        state_before = round_controller.state
        player = round_controller.current_turn_player()
        move = round_controller.run_bot_turn()
        self._last_visible_state = round_controller.state
        events.append(self._build_move_event(player, move, is_bot=True, state_before=state_before,
                                             state_after=round_controller.state))

    def _advance_finished_round(self, round_controller: RoundController, events: list[SessionEvent]) -> None:
        """Finalize the finished round and push the game-level score update."""
        if round_controller.state is not None:
            # Preserve the just-finished round state for rendering while the game
            # controller clears out the active round reference.
            self._last_visible_state = round_controller.state

        round_result = self.game_controller.finalize_current_round()
        events.append(
            SessionEvent(
                "round_finished",
                {
                    "round_num": round_result.round_num,
                    "total_rounds": self.game_controller.n_players,
                    "end_reason": round_result.end_reason,
                    "scores_in": list(round_result.scores_in),
                    "scores_out": list(round_result.scores_out),
                },
            )
        )

    # ------------------ Event helpers

    def _build_round_started_event(self, round_controller: RoundController) -> SessionEvent:
        """Convert round-start controller data into a small UI event payload."""
        return SessionEvent(
            "round_started",
            {
                "round_num": round_controller.round_num,
                "total_rounds": self.game_controller.n_players,
                "n_players": round_controller.n_players,
            },
        )

    def _build_move_event(self, player: int, move: Move, *, is_bot: bool, state_before: GameState, state_after: GameState) -> SessionEvent:
        """Wrap one resolved move with enough context for human-readable logging."""
        return SessionEvent(
            "move_submitted",
            {
                "player": player,
                "move": move,
                "is_bot": is_bot,
                "context": build_move_details(player, move, state_before, state_after),
            },
        )

