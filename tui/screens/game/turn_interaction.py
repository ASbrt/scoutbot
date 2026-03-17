from __future__ import annotations

from typing import TYPE_CHECKING

from engine.state.GameState import ScoutAndShowMove, ScoutCandidate, ScoutMove, ShowMove

from .turn_input import HumanTurnPhase

if TYPE_CHECKING:
    from .game_screen import GameScreen


class TurnInteractionController:
    """Owns all human-turn input handling and move matching for GameScreen."""

    def __init__(self, screen: "GameScreen") -> None:
        self.screen = screen

    def choose_show(self) -> None:
        if not self._waiting_for_human_turn() or self.screen.turn_input.phase != HumanTurnPhase.ACTION_CHOICE:
            return
        if not self._has_show_move():
            self.screen.logger.log_error("Show not legal right now!")
            return

        self.screen.turn_input.start_show_select()
        self.screen.presenter.refresh()

    def choose_scout(self) -> None:
        if not self._waiting_for_human_turn() or self.screen.turn_input.phase != HumanTurnPhase.ACTION_CHOICE:
            return
        self._start_scout_flow(is_scout_and_show=False)

    def choose_scout_and_show(self) -> None:
        if not self._waiting_for_human_turn() or self.screen.turn_input.phase != HumanTurnPhase.ACTION_CHOICE:
            return
        self._start_scout_flow(is_scout_and_show=True)

    def cursor_left(self) -> None:
        if not self._waiting_for_human_turn():
            return

        phase = self.screen.turn_input.phase
        if phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            self.screen.turn_input.cursor_index = 0
        elif phase in (HumanTurnPhase.SHOW_SELECT, HumanTurnPhase.SCOUT_INSERT_POS):
            hand_len = len(self._current_hand())
            limit = hand_len + 1 if phase == HumanTurnPhase.SCOUT_INSERT_POS else hand_len
            if limit:
                self.screen.turn_input.cursor_index = (self.screen.turn_input.cursor_index - 1) % limit
        self.screen.presenter.refresh()

    def cursor_right(self) -> None:
        if not self._waiting_for_human_turn():
            return

        phase = self.screen.turn_input.phase
        if phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            table_cards = self._current_table_cards()
            if table_cards:
                self.screen.turn_input.cursor_index = len(table_cards) - 1
        elif phase in (HumanTurnPhase.SHOW_SELECT, HumanTurnPhase.SCOUT_INSERT_POS):
            hand_len = len(self._current_hand())
            limit = hand_len + 1 if phase == HumanTurnPhase.SCOUT_INSERT_POS else hand_len
            if limit:
                self.screen.turn_input.cursor_index = (self.screen.turn_input.cursor_index + 1) % limit
        self.screen.presenter.refresh()

    def toggle_selection(self) -> None:
        if not self._waiting_for_human_turn():
            return

        phase = self.screen.turn_input.phase
        if phase == HumanTurnPhase.SHOW_SELECT:
            if self.screen.turn_input.cursor_index in self.screen.turn_input.selected_indices:
                self.screen.turn_input.selected_indices.remove(self.screen.turn_input.cursor_index)
            else:
                self.screen.turn_input.selected_indices.add(self.screen.turn_input.cursor_index)
        elif phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            if self.screen.turn_input.scouted_table_index == self.screen.turn_input.cursor_index:
                self.screen.turn_input.scouted_table_index = None
            else:
                self.screen.turn_input.scouted_table_index = self.screen.turn_input.cursor_index
        elif phase == HumanTurnPhase.SCOUT_INSERT_ORIENTATION:
            self.screen.turn_input.toggle_scout_flip()
        else:
            return

        self.screen.presenter.refresh()

    def confirm_action(self) -> None:
        if not self._waiting_for_human_turn():
            return

        try:
            phase = self.screen.turn_input.phase
            if phase == HumanTurnPhase.SHOW_SELECT:
                self._try_show()
            elif phase == HumanTurnPhase.SCOUT_CARD_SELECT:
                self._confirm_scout_target()
            elif phase == HumanTurnPhase.SCOUT_INSERT_ORIENTATION:
                self._confirm_scout_orientation()
            elif phase == HumanTurnPhase.SCOUT_INSERT_POS:
                self._finalize_scout()
            elif phase == HumanTurnPhase.ACTION_CHOICE:
                self.screen.logger.log_info("Choose an available action first (S/C/A)")
        except Exception as exc:
            self.screen.logger.log_error(f"Error during confirm: {exc}")

    def cancel_action(self) -> None:
        """Allow backing out of a chosen move type and returning to action choice."""
        if not self._waiting_for_human_turn() or self.screen.turn_input.phase == HumanTurnPhase.ACTION_CHOICE:
            return

        self.screen.turn_input.cancel()
        self.screen.logger.log_info("Action cancelled. Choose another move type.")
        self.screen.presenter.refresh()

    def handle_orientation_key(self, key: str) -> bool:
        if not self._waiting_for_human_turn() or self.screen.turn_input.phase != HumanTurnPhase.SCOUT_INSERT_ORIENTATION:
            return False

        if key in ["y", "u", "up"]:
            self.screen.turn_input.scout_flip = False
            self._confirm_scout_orientation()
            return True
        if key in ["n", "d", "down"]:
            self.screen.turn_input.scout_flip = True
            self._confirm_scout_orientation()
            return True
        return False

    def _try_show(self) -> None:
        """Match the current contiguous selection to a legal Show or Scout&Show move."""
        if not self.screen.turn_input.selected_indices:
            self.screen.logger.log_info("No cards selected! Select contiguous cards with SPACE first.")
            return

        start = min(self.screen.turn_input.selected_indices)
        length = max(self.screen.turn_input.selected_indices) - start + 1
        if len(self.screen.turn_input.selected_indices) != length:
            self.screen.logger.log_error("Invalid Selection: Cards must be contiguous.")
            return

        matching_move = None
        if self.screen.turn_input.is_scout_and_show:
            for move in self._legal_moves():
                if not isinstance(move, ScoutAndShowMove):
                    continue
                if (
                    move.candidate.scout == self.screen.turn_input.sas_scout_candidate
                    and move.candidate.show.start == start
                    and move.candidate.show.length == length
                ):
                    matching_move = move
                    break
        else:
            for move in self._show_moves():
                if move.candidate.start == start and move.candidate.length == length:
                    matching_move = move
                    break

        if matching_move is None:
            self.screen.logger.log_error("Move rejected! (Invalid pattern or doesn't beat table)")
            return

        self._submit_human_move(matching_move)

    def _start_scout_flow(self, *, is_scout_and_show: bool) -> None:
        """Begin the UI-only scout building flow from controller-provided legal moves."""
        if is_scout_and_show:
            moves_to_consider = self._scout_and_show_moves()
            if not moves_to_consider:
                self.screen.logger.log_error("Scout & Show not legal right now!")
                return
            scout_candidates = {move.candidate.scout for move in moves_to_consider}
        else:
            moves_to_consider = self._scout_moves()
            if not moves_to_consider:
                self.screen.logger.log_error("Scout not legal right now!")
                return
            scout_candidates = {move.candidate for move in moves_to_consider}

        table_indices = sorted({candidate.table_index for candidate in scout_candidates})
        self.screen.turn_input.start_scout_flow(is_scout_and_show=is_scout_and_show)
        self.screen.turn_input.cursor_index = table_indices[0]
        self.screen.logger.log_info("Scouting... Move to a table-end card, press Space to select, then Enter.")

        self.screen.presenter.refresh()

    def _finalize_scout(self) -> None:
        """Resolve the final scout parameters into one legal move, if available."""
        candidate = ScoutCandidate(
            table_index=self.screen.turn_input.scouted_table_index,
            hand_insert_index=self.screen.turn_input.cursor_index,
            flip=self.screen.turn_input.scout_flip,
        )

        if self.screen.turn_input.is_scout_and_show:
            valid_candidate = any(
                isinstance(move, ScoutAndShowMove) and move.candidate.scout == candidate
                for move in self._legal_moves()
            )
            if not valid_candidate:
                self.screen.logger.log_error("This scout move is not part of any legal Scout & Show.")
                self.screen.turn_input.cancel()
                self.screen.presenter.refresh()
                return

            self.screen.turn_input.start_scout_and_show_select(candidate)
            self.screen.logger.log_info("Scouted! Now select cards to show (contiguous).")
            self.screen.presenter.refresh()
            return

        matching_move = next(
            (move for move in self._scout_moves() if move.candidate == candidate),
            None,
        )
        if matching_move is None:
            self.screen.logger.log_error("That scout move is not legal.")
            self.screen.turn_input.cancel()
            self.screen.presenter.refresh()
            return

        self._submit_human_move(matching_move)

    def _confirm_scout_target(self) -> None:
        """Lock in the chosen table card and move to orientation selection."""
        if self.screen.turn_input.scouted_table_index is None:
            self.screen.logger.log_info("Press Space to select a table card first.")
            return

        self.screen.turn_input.start_orientation_select()
        self.screen.presenter.refresh()

    def _confirm_scout_orientation(self) -> None:
        """Lock in the orientation and move to insertion-position selection."""
        self.screen.turn_input.start_scout_insert(self.screen.turn_input.scouted_table_index)
        self.screen.presenter.refresh()

    def _submit_human_move(self, move) -> None:
        """Pass the completed move back to the screen's session orchestration."""
        self.screen._submit_human_move(move)

    def preview_state(self):
        """Return a non-authoritative preview state for render-time scout previews."""
        if not self._waiting_for_human_turn():
            return None

        round_controller = self.screen.session.round_controller if self.screen.session else None
        if round_controller is None or round_controller.state is None:
            return None

        if (
            self.screen.turn_input.phase == HumanTurnPhase.SCOUT_INSERT_POS
            and self.screen.turn_input.scouted_table_index is not None
        ):
            candidate = ScoutCandidate(
                table_index=self.screen.turn_input.scouted_table_index,
                hand_insert_index=self.screen.turn_input.cursor_index,
                flip=self.screen.turn_input.scout_flip,
            )
            return round_controller.preview_scout_candidate(candidate)

        if (
            self.screen.turn_input.phase == HumanTurnPhase.SHOW_SELECT
            and self.screen.turn_input.is_scout_and_show
            and self.screen.turn_input.sas_scout_candidate is not None
        ):
            return round_controller.preview_scout_candidate(self.screen.turn_input.sas_scout_candidate)

        return None

    def preview_scout_card(self):
        """Return the currently selected scout card, with orientation preview applied."""
        if self.screen.turn_input.scouted_table_index is None:
            return None

        table_cards = self._current_table_cards()
        if not table_cards:
            return None

        card = table_cards[self.screen.turn_input.scouted_table_index]
        return card.flip_card() if self.screen.turn_input.scout_flip else card

    def _waiting_for_human_turn(self) -> bool:
        return self.screen.session is not None and self.screen.session.waiting_for_human_turn()

    def _legal_moves(self) -> list:
        round_controller = self.screen.session.round_controller if self.screen.session else None
        return round_controller.legal_moves if round_controller is not None else []

    def _current_hand(self):
        round_controller = self.screen.session.round_controller if self.screen.session else None
        if round_controller is None or round_controller.state is None:
            return []
        return round_controller.state.hands[round_controller.state.current_player]

    def _current_table_cards(self):
        round_controller = self.screen.session.round_controller if self.screen.session else None
        if round_controller is None or round_controller.state is None or round_controller.state.table is None:
            return []
        return round_controller.state.table.cards

    def _show_moves(self) -> list[ShowMove]:
        return [move for move in self._legal_moves() if isinstance(move, ShowMove)]

    def _scout_moves(self) -> list[ScoutMove]:
        return [move for move in self._legal_moves() if isinstance(move, ScoutMove)]

    def _scout_and_show_moves(self) -> list[ScoutAndShowMove]:
        return [move for move in self._legal_moves() if isinstance(move, ScoutAndShowMove)]

    def _has_show_move(self) -> bool:
        return bool(self._show_moves())
