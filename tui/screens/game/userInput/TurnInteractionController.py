"""Human-input controller that converts key presses into moves."""

from typing import TYPE_CHECKING
from engine.state.GameState import ScoutAndShowMove, ScoutCandidate, ScoutMove, ShowMove
from tui.screens.game.userInput.HumanInputUIState import HumanTurnPhase
if TYPE_CHECKING:
    from tui.screens.game.GameScreen import GameScreen


class TurnInteractionController:
    """Owns all human-turn input handling and move matching for GameScreen."""

    def __init__(self, screen: "GameScreen") -> None:
        self.screen = screen

    def choose_show(self) -> None:
        """Enter the contiguous hand-card selection flow for a Show move."""
        if not self._waiting_for_human_turn() or self.screen.input_state.phase != HumanTurnPhase.ACTION_CHOICE:
            return
        if not self._has_show_move():
            self.screen.logger.log_error("Show not legal right now!")
            return

        self.screen.input_state.start_show_select()
        self.screen.renderer.refresh()

    def choose_scout(self) -> None:
        """Enter the scout-building flow if a plain Scout is legal."""
        if not self._waiting_for_human_turn() or self.screen.input_state.phase != HumanTurnPhase.ACTION_CHOICE:
            return
        self._start_scout_flow(is_scout_and_show=False)

    def choose_scout_and_show(self) -> None:
        """Enter the scout-first flow for a Scout & Show move."""
        if not self._waiting_for_human_turn() or self.screen.input_state.phase != HumanTurnPhase.ACTION_CHOICE:
            return
        self._start_scout_flow(is_scout_and_show=True)

    def cursor_left(self) -> None:
        """Move the active cursor left within the current human sub-phase."""
        if not self._waiting_for_human_turn():
            return

        phase = self.screen.input_state.phase
        if phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            # Only table-end cards are scoutable, so "left" snaps to the first end.
            self.screen.input_state.cursor_index = 0
        elif phase in (HumanTurnPhase.SHOW_SELECT, HumanTurnPhase.SCOUT_INSERT_POS):
            hand_len = len(self._current_hand())
            limit = hand_len + 1 if phase == HumanTurnPhase.SCOUT_INSERT_POS else hand_len
            if limit:
                self.screen.input_state.cursor_index = (self.screen.input_state.cursor_index - 1) % limit
        self.screen.renderer.refresh()

    def cursor_right(self) -> None:
        """Move the active cursor right within the current human sub-phase."""
        if not self._waiting_for_human_turn():
            return

        phase = self.screen.input_state.phase
        if phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            table_cards = self._current_table_cards()
            if table_cards:
                # Symmetric with cursor_left: jump to the far scoutable table end.
                self.screen.input_state.cursor_index = len(table_cards) - 1
        elif phase in (HumanTurnPhase.SHOW_SELECT, HumanTurnPhase.SCOUT_INSERT_POS):
            hand_len = len(self._current_hand())
            limit = hand_len + 1 if phase == HumanTurnPhase.SCOUT_INSERT_POS else hand_len
            if limit:
                self.screen.input_state.cursor_index = (self.screen.input_state.cursor_index + 1) % limit
        self.screen.renderer.refresh()

    def toggle_selection(self) -> None:
        """Toggle whichever item is selectable in the current human sub-phase."""
        if not self._waiting_for_human_turn():
            return

        phase = self.screen.input_state.phase
        if phase == HumanTurnPhase.SHOW_SELECT:
            if self.screen.input_state.cursor_index in self.screen.input_state.selected_indices:
                self.screen.input_state.selected_indices.remove(self.screen.input_state.cursor_index)
            else:
                self.screen.input_state.selected_indices.add(self.screen.input_state.cursor_index)
        elif phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            if self.screen.input_state.scouted_table_index == self.screen.input_state.cursor_index:
                self.screen.input_state.scouted_table_index = None
            else:
                self.screen.input_state.scouted_table_index = self.screen.input_state.cursor_index
        elif phase == HumanTurnPhase.SCOUT_INSERT_ORIENTATION:
            self.screen.input_state.toggle_scout_flip()
        else:
            return

        self.screen.renderer.refresh()

    def confirm_action(self) -> None:
        """Advance the current human flow or submit the completed move."""
        if not self._waiting_for_human_turn():
            return

        try:
            phase = self.screen.input_state.phase
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
            # Logging here keeps the TUI responsive while still surfacing unexpected
            # input-flow errors to the user.
            self.screen.logger.log_error(f"Error during confirm: {exc}")

    def cancel_action(self) -> None:
        """Allow backing out of a chosen move type and returning to action choice."""
        if not self._waiting_for_human_turn() or self.screen.input_state.phase == HumanTurnPhase.ACTION_CHOICE:
            return

        self.screen.input_state.cancel()
        self.screen.logger.log_info("Action cancelled. Choose another move type.")
        self.screen.renderer.refresh()

    def handle_orientation_key(self, key: str) -> bool:
        """Support quick yes/no style keys during scout-card orientation choice."""
        if not self._waiting_for_human_turn() or self.screen.input_state.phase != HumanTurnPhase.SCOUT_INSERT_ORIENTATION:
            return False

        if key in ["y", "u", "up"]:
            self.screen.input_state.scout_flip = False
            self._confirm_scout_orientation()
            return True
        if key in ["n", "d", "down"]:
            self.screen.input_state.scout_flip = True
            self._confirm_scout_orientation()
            return True
        return False

    def _try_show(self) -> None:
        """Match the current contiguous selection to a legal Show or Scout&Show move."""
        if not self.screen.input_state.selected_indices:
            self.screen.logger.log_info("No cards selected! Select contiguous cards with SPACE first.")
            return

        start = min(self.screen.input_state.selected_indices)
        length = max(self.screen.input_state.selected_indices) - start + 1
        if len(self.screen.input_state.selected_indices) != length:
            self.screen.logger.log_error("Invalid Selection: Cards must be contiguous.")
            return

        matching_move = None
        if self.screen.input_state.is_scout_and_show:
            # The UI never invents moves. It searches the controller-produced legal
            # list for one whose scout half and show span match the current choices.
            for move in self._legal_moves():
                if not isinstance(move, ScoutAndShowMove):
                    continue
                if (
                    move.candidate.scout == self.screen.input_state.sas_scout_candidate
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

        # The controller may expose multiple moves that share the same table target,
        # so the UI deduplicates them into one target-selection step first.
        table_indices = sorted({candidate.table_index for candidate in scout_candidates})
        self.screen.input_state.start_scout_flow(is_scout_and_show=is_scout_and_show)
        self.screen.input_state.cursor_index = table_indices[0]
        self.screen.logger.log_info("Scouting... Move to a table-end card, press Space to select, then Enter.")

        self.screen.renderer.refresh()

    def _finalize_scout(self) -> None:
        """Resolve the final scout parameters into one legal move, if available."""
        candidate = ScoutCandidate(
            # These three fields are the complete controller-side definition of a
            # scout action, so the UI packages them up and then matches them against
            # the legal move list instead of applying anything directly.
            table_index=self.screen.input_state.scouted_table_index,
            hand_insert_index=self.screen.input_state.cursor_index,
            flip=self.screen.input_state.scout_flip,
        )

        if self.screen.input_state.is_scout_and_show:
            valid_candidate = any(
                isinstance(move, ScoutAndShowMove) and move.candidate.scout == candidate
                for move in self._legal_moves()
            )
            if not valid_candidate:
                self.screen.logger.log_error("This scout move is not part of any legal Scout & Show.")
                self.screen.input_state.cancel()
                self.screen.renderer.refresh()
                return

            self.screen.input_state.start_scout_and_show_select(candidate)
            self.screen.logger.log_info("Scouted! Now select cards to show (contiguous).")
            self.screen.renderer.refresh()
            return

        matching_move = next(
            # `next(..., None)` is a compact "find the exact legal move object"
            # helper so we submit controller-approved moves only.
            (move for move in self._scout_moves() if move.candidate == candidate),
            None,
        )
        if matching_move is None:
            self.screen.logger.log_error("That scout move is not legal.")
            self.screen.input_state.cancel()
            self.screen.renderer.refresh()
            return

        self._submit_human_move(matching_move)

    def _confirm_scout_target(self) -> None:
        """Lock in the chosen table card and move to orientation selection."""
        if self.screen.input_state.scouted_table_index is None:
            self.screen.logger.log_info("Press Space to select a table card first.")
            return

        self.screen.input_state.start_orientation_select()
        self.screen.renderer.refresh()

    def _confirm_scout_orientation(self) -> None:
        """Lock in the orientation and move to insertion-position selection."""
        self.screen.input_state.start_scout_insert(self.screen.input_state.scouted_table_index)
        self.screen.renderer.refresh()

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
            self.screen.input_state.phase == HumanTurnPhase.SCOUT_INSERT_POS
            and self.screen.input_state.scouted_table_index is not None
        ):
            # This preview lets the presenter show where the scouted card would land
            # before the move is actually submitted to the controller.
            candidate = ScoutCandidate(
                table_index=self.screen.input_state.scouted_table_index,
                hand_insert_index=self.screen.input_state.cursor_index,
                flip=self.screen.input_state.scout_flip,
            )
            return round_controller.preview_scout_candidate(candidate)

        if (
            self.screen.input_state.phase == HumanTurnPhase.SHOW_SELECT
            and self.screen.input_state.is_scout_and_show
            and self.screen.input_state.sas_scout_candidate is not None
        ):
            # Once the scout half is fixed, the preview state reflects that pending
            # scout while the player decides which cards to show next.
            return round_controller.preview_scout_candidate(self.screen.input_state.sas_scout_candidate)

        return None

    def preview_scout_card(self):
        """Return the currently selected scout card, with orientation preview applied."""
        if self.screen.input_state.scouted_table_index is None:
            return None

        table_cards = self._current_table_cards()
        if not table_cards:
            return None

        card = table_cards[self.screen.input_state.scouted_table_index]
        return card.flip_card() if self.screen.input_state.scout_flip else card

    def _waiting_for_human_turn(self) -> bool:
        """Short helper so the input layer can cheaply gate every action."""
        return self.screen.session is not None and self.screen.session.waiting_for_human_turn()

    def _legal_moves(self) -> list:
        """Read the authoritative move list from the active round controller."""
        round_controller = self.screen.session.round_controller if self.screen.session else None
        return round_controller.legal_moves if round_controller is not None else []

    def _current_hand(self):
        """Return the acting player's current hand from controller state."""
        round_controller = self.screen.session.round_controller if self.screen.session else None
        if round_controller is None or round_controller.state is None:
            return []
        return round_controller.state.hands[round_controller.state.current_player]

    def _current_table_cards(self):
        """Return the table cards from the authoritative controller state."""
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
