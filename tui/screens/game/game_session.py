from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from engine.controllers.GameController import GameController
from engine.controllers.RoundController import RoundController, RoundStage
from engine.logic.legal_moves import apply_scout_move
from engine.state.CardCore import Card
from engine.state.GameState import GameState, Move, ScoutAndShowMove, ScoutMove, ShowMove
from tools.Logging import GameResult


@dataclass(frozen=True)
class SessionEvent:
    """Structured, UI-agnostic events emitted while the session advances."""

    kind: str
    data: dict = field(default_factory=dict)


class GameSession:
    """
    Small orchestration wrapper for the TUI.

    RoundController already knows how to run one round, but the screen also needs a
    place that can bridge rounds, finalize scores through GameController, and stop
    cleanly when a human decision is needed. That is why this layer exists.
    """

    def __init__(
        self, *, seed: int, bots: list, rng: random.Random, n_players: int, game_id: int = 0, log_turns: bool = True
    ) -> None:
        self.game_controller = GameController(
            game_id=game_id,
            seed=seed,
            bots=bots,
            rng=rng,
            n_players=n_players,
            log_turns=log_turns,
        )
        self._last_visible_state: Optional[GameState] = None
        self._final_result: Optional[GameResult] = None

    @property
    def round_controller(self) -> Optional[RoundController]:
        return self.game_controller.current_round

    @property
    def display_state(self) -> Optional[GameState]:
        round_controller = self.round_controller
        if round_controller is not None and round_controller.state is not None:
            return round_controller.state
        return self._last_visible_state

    @property
    def scores(self) -> list[int]:
        state = self.display_state
        if state is not None:
            return list(state.scores)
        return list(self.game_controller.scores)

    def start(self) -> list[SessionEvent]:
        """Start the first round and return the initial session events."""
        if self.round_controller is not None or self._final_result is not None:
            raise RuntimeError("GameSession has already been started")

        round_controller = self.game_controller.start_next_round()
        return [self._build_round_started_event(round_controller)]

    def advance_until_human_or_end(self) -> list[SessionEvent]:
        """
        Keep advancing controllers until the UI needs to step in again.

        This is intentionally broader than RoundController's bot helpers because the
        TUI needs one call that can cross round boundaries and eventually finish the
        whole game, not just one stage inside one round.
        """
        events: list[SessionEvent] = []

        while True:
            round_controller = self.round_controller

            if round_controller is None:
                if not self._advance_game_level(events):
                    break
                continue

            if round_controller.stage == RoundStage.FLIP:
                if self._waiting_for_human_flip(round_controller):
                    break
                self._advance_flip_stage(round_controller, events)
                continue

            if round_controller.stage == RoundStage.TURNS:
                if self._waiting_for_human_turn(round_controller):
                    break
                self._advance_turn_stage(round_controller, events)
                continue

            if round_controller.stage == RoundStage.FINISHED:
                self._advance_finished_round(round_controller, events)
                break

            raise RuntimeError(f"Unexpected round stage: {round_controller.stage}")

        return events

    def submit_flip(self, flipped: bool) -> list[SessionEvent]:
        """Submit the current human flip choice."""
        round_controller = self._require_round_controller()
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

    def submit_move(self, move: Move) -> list[SessionEvent]:
        """Submit one complete human move object to the controller."""
        round_controller = self._require_round_controller()
        if round_controller.stage != RoundStage.TURNS or round_controller.state is None:
            raise RuntimeError("submit_move is only valid during turn phase")
        if round_controller.current_actor_is_bot():
            raise RuntimeError("submit_move cannot be used for a bot actor")

        state_before = round_controller.state
        player = round_controller.current_turn_player()
        round_controller.apply_selected_move(move)
        self._last_visible_state = round_controller.state
        return [
            self._build_move_event(player, move, is_bot=False, state_before=state_before, state_after=round_controller.state)
        ]

    def waiting_for_human_flip(self) -> bool:
        round_controller = self.round_controller
        return round_controller is not None and self._waiting_for_human_flip(round_controller)

    def waiting_for_human_turn(self) -> bool:
        round_controller = self.round_controller
        return round_controller is not None and self._waiting_for_human_turn(round_controller)

    def is_game_over(self) -> bool:
        return self._final_result is not None

    def get_final_result(self) -> Optional[GameResult]:
        return self._final_result

    def _require_round_controller(self) -> RoundController:
        round_controller = self.round_controller
        if round_controller is None:
            raise RuntimeError("No active round controller")
        return round_controller

    def _advance_game_level(self, events: list[SessionEvent]) -> bool:
        """Handle either starting the next round or finishing the full game."""
        if self.game_controller.is_finished:
            if self._final_result is None:
                self._final_result = self.game_controller.build_result()
                events.append(
                    SessionEvent("game_finished", {"scores_final": list(self._final_result.scores_final)})
                )
            return False

        round_controller = self.game_controller.start_next_round()
        events.append(self._build_round_started_event(round_controller))
        return True

    def _advance_flip_stage(
        self, round_controller: RoundController, events: list[SessionEvent]
    ) -> None:
        """Resolve exactly one bot flip step."""
        player = round_controller.current_flip_player()
        flipped = round_controller.run_bot_flip_step()
        events.append(
            SessionEvent(
                "flip_submitted",
                {"player": player, "flipped": flipped, "is_bot": True},
            )
        )

    def _advance_turn_stage(
        self, round_controller: RoundController, events: list[SessionEvent]
    ) -> None:
        """Resolve exactly one bot move step."""
        if round_controller.state is None:
            raise RuntimeError("RoundController is in TURNS stage without state")

        state_before = round_controller.state
        player = round_controller.current_turn_player()
        move = round_controller.run_bot_turn()
        self._last_visible_state = round_controller.state
        events.append(
            self._build_move_event(player, move, is_bot=True, state_before=state_before, state_after=round_controller.state)
        )

    def _advance_finished_round(
        self, round_controller: RoundController, events: list[SessionEvent]
    ) -> None:
        """Finalize the finished round and push the game-level score update."""
        if round_controller.state is not None:
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

    def _build_round_started_event(
        self, round_controller: RoundController
    ) -> SessionEvent:
        return SessionEvent(
            "round_started",
            {
                "round_num": round_controller.round_num,
                "total_rounds": self.game_controller.n_players,
                "n_players": round_controller.n_players,
            },
        )

    def _build_move_event(self, player: int, move: Move, *, is_bot: bool, state_before: GameState, state_after: GameState) -> SessionEvent:
        return SessionEvent(
            "move_submitted",
            {
                "player": player,
                "move": move,
                "is_bot": is_bot,
                "context": self._build_move_context(player, move, state_before, state_after),
            },
        )

    def _build_move_context(self, player: int, move: Move, state_before: GameState, state_after: GameState) -> dict:
        score_delta = [after - before for before, after in zip(state_before.scores, state_after.scores)]

        if isinstance(move, ShowMove):
            start = move.candidate.start
            end = start + move.candidate.length
            return {
                "cards": tuple(state_before.hands[player][start:end]),
                "score_delta": score_delta,
            }

        if isinstance(move, ScoutMove):
            scout_card = self._scouted_card_from_state(state_before, move.candidate.table_index)
            return {
                "scout_card": scout_card,
                "scout_result_card": scout_card.flip_card() if scout_card and move.candidate.flip else scout_card,
                "score_delta": score_delta,
            }

        if isinstance(move, ScoutAndShowMove):
            scout_card = self._scouted_card_from_state(state_before, move.candidate.scout.table_index)
            scout_state = apply_scout_move(state_before, move.candidate.scout, advance_turn=False)
            start = move.candidate.show.start
            end = start + move.candidate.show.length
            return {
                "scout_card": scout_card,
                "scout_result_card": scout_card.flip_card() if scout_card and move.candidate.scout.flip else scout_card,
                "cards": tuple(scout_state.hands[player][start:end]),
                "score_delta": score_delta,
            }

        return {"score_delta": score_delta}

    def _scouted_card_from_state(self, state: GameState, table_index: int) -> Optional[Card]:
        if state.table is None or table_index >= len(state.table.cards):
            return None
        return state.table.cards[table_index]

    def _waiting_for_human_flip(self, round_controller: RoundController) -> bool:
        return round_controller.stage == RoundStage.FLIP and not round_controller.current_actor_is_bot()

    def _waiting_for_human_turn(self, round_controller: RoundController) -> bool:
        return round_controller.stage == RoundStage.TURNS and not round_controller.current_actor_is_bot()
