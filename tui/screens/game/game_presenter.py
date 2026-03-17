from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Button, Static

from engine.controllers.RoundController import RoundController, RoundStage
from engine.state.GameState import ScoutAndShowMove, ScoutMove, ShowMove

from ...render_cards import render_card_row
from .turn_input import HumanTurnPhase
from .widgets import PlayerSummary

if TYPE_CHECKING:
    from .game_screen import GameScreen


class GamePresenter:
    """Owns all widget-refresh and view-rendering logic for GameScreen."""

    def __init__(self, screen: "GameScreen") -> None:
        self.screen = screen

    def refresh(self) -> None:
        """Refresh the visible widgets from the current session/controller state."""
        if self.screen.session is None:
            return

        round_controller = self.screen.session.round_controller

        if self.screen.session.is_game_over():
            self._refresh_game_over_view()
            return

        if round_controller is None:
            return

        if round_controller.stage == RoundStage.FLIP:
            self._refresh_flip_view(round_controller)
            return

        if round_controller.stage == RoundStage.TURNS and round_controller.state is not None:
            self._refresh_turn_view(round_controller.state)
            return

        self._set_controls_enabled(False)

    def _refresh_game_over_view(self) -> None:
        """Show the final frozen state after GameController has finished all rounds."""
        status = self.screen.query_one("#game_status", Static)
        hand_area = self.screen.query_one("#hand_area", Static)
        hint = self.screen.query_one("#interaction_hint", Static)
        player_summary = self.screen.query_one("#player_summary", PlayerSummary)
        resource_info = self.screen.query_one("#resource_info", Static)

        status.update(f"Game Over ({self.screen.config.n_players}/{self.screen.config.n_players})")
        self._render_table(self.screen.query_one("#table_area", Static), cards=[])
        self._render_last_hand(hand_area)
        hint.visible = True
        hint.update("Game finished. Press Exit to return.")

        display_state = self.screen.session.display_state
        if display_state is not None:
            player_summary.update_summary(display_state, self.screen.bots, current_player_idx=display_state.current_player)
        else:
            player_summary.update_summary(
                bots=self.screen.bots,
                current_player_idx=0,
                scores=self.screen.session.get_final_result().scores_final,
                hand_sizes=[0] * self.screen.config.n_players,
                tokens=["--"] * self.screen.config.n_players,
            )

        resource_info.update(f"Completed {self.screen.config.n_players}/{self.screen.config.n_players} rounds.")
        self._set_controls_enabled(False)

    def _refresh_flip_view(self, round_controller: RoundController) -> None:
        """Render the pre-round flip stage from RoundController.pending_hands."""
        status = self.screen.query_one("#game_status", Static)
        hand_area = self.screen.query_one("#hand_area", Static)
        hint = self.screen.query_one("#interaction_hint", Static)
        player_summary = self.screen.query_one("#player_summary", PlayerSummary)
        resource_info = self.screen.query_one("#resource_info", Static)

        current_player = round_controller.current_flip_player()
        hand = round_controller.get_flip_hand()
        hand_sizes = [len(cards) for cards in round_controller.pending_hands]

        status.update(f"Round: {round_controller.round_num}/{self.screen.config.n_players} (Flip)")
        self._render_table(self.screen.query_one("#table_area", Static), cards=[])
        hand_area.update(render_card_row(hand))
        hint.visible = True
        if self.screen.bots[current_player] is None:
            hint.update("Choose hand orientation in the flip modal.")
        else:
            hint.update("Waiting for bot flip decision...")

        player_summary.update_summary(
            bots=self.screen.bots,
            current_player_idx=current_player,
            scores=self.screen.session.scores,
            hand_sizes=hand_sizes,
            tokens=[True] * self.screen.config.n_players,
        )
        resource_info.update(
            f"Round {round_controller.round_num}/{self.screen.config.n_players} | "
            f"Current flip: {'YOU' if self.screen.bots[current_player] is None else f'P{current_player} (Bot)'}"
        )
        self._set_controls_enabled(False)

    def _refresh_turn_view(self, state) -> None:
        """Render the main turn stage from RoundController.state and legal moves."""
        status = self.screen.query_one("#game_status", Static)
        hand_area = self.screen.query_one("#hand_area", Static)
        hint = self.screen.query_one("#interaction_hint", Static)
        player_summary = self.screen.query_one("#player_summary", PlayerSummary)
        resource_info = self.screen.query_one("#resource_info", Static)

        current_player = state.current_player
        preview_state = self.screen.turn_interaction.preview_state() if self.screen.session.waiting_for_human_turn() else None
        display_state = preview_state or state
        hand = display_state.hands[current_player]
        table_cards = list(display_state.table.cards) if display_state.table else []

        status.update(f"Round: {state.round_num}/{self.screen.config.n_players}")
        self._render_table(
            self.screen.query_one("#table_area", Static),
            cards=table_cards,
            selected_indices=self._table_selection(),
            cursor_indices=self._table_cursor(),
        )
        player_summary.update_summary(state, self.screen.bots, current_player_idx=current_player)

        resource_info.update(
            f"Round {state.round_num}/{self.screen.config.n_players} | "
            f"Active: {'YOU' if self.screen.bots[current_player] is None else f'P{current_player} (Bot)'}"
        )

        if self.screen.session.waiting_for_human_turn():
            self._render_human_turn(hand_area, hint, hand)
            self._set_controls_enabled(self.screen.turn_input.phase == HumanTurnPhase.ACTION_CHOICE)
            return

        self._render_bot_turn(hand_area, hint, hand, current_player)
        self._set_controls_enabled(False)

    def _table_cursor(self) -> set[int]:
        """Only show a table cursor while the human is picking a scout target."""
        if self.screen.session.waiting_for_human_turn() and self.screen.turn_input.phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            return {self.screen.turn_input.cursor_index}
        return set()

    def _table_selection(self) -> set[int]:
        if (
            self.screen.session.waiting_for_human_turn()
            and self.screen.turn_input.scouted_table_index is not None
            and self.screen.turn_input.phase in (HumanTurnPhase.SCOUT_CARD_SELECT, HumanTurnPhase.SCOUT_INSERT_ORIENTATION)
        ):
            return {self.screen.turn_input.scouted_table_index}
        return set()

    def _render_human_turn(self, hand_area: Static, hint: Static, hand) -> None:
        """Render the hand and hint text for the active human sub-phase."""
        hand_cursor = set()
        phase = self.screen.turn_input.phase

        if phase == HumanTurnPhase.SHOW_SELECT:
            hand_cursor = {self.screen.turn_input.cursor_index}
            hand_area.update(
                render_card_row(
                    hand,
                    selected_indices=self.screen.turn_input.selected_indices,
                    cursor_indices=hand_cursor,
                )
            )
            hint.update("Select cards (Arrow Keys + Space), Enter to confirm, Esc to choose a different move.")
        elif phase == HumanTurnPhase.SCOUT_INSERT_POS:
            if hand:
                hand_cursor = {self.screen.turn_input.cursor_index}
            hand_area.update(render_card_row(hand, cursor_indices=hand_cursor))
            hint.update("Move the preview card through your hand, Enter to confirm, Esc to choose a different move.")
        elif phase == HumanTurnPhase.SCOUT_CARD_SELECT:
            hand_area.update(render_card_row(hand))
            hint.update("Move to a table-end card, Space to select, Enter to confirm, Esc to choose a different move.")
        elif phase == HumanTurnPhase.SCOUT_INSERT_ORIENTATION:
            preview_card = self.screen.turn_interaction.preview_scout_card()
            if preview_card is None:
                hand_area.update(render_card_row(hand))
            else:
                hand_area.update(render_card_row(hand) + "\n\nScouted card preview:\n" + render_card_row([preview_card]))
            hint.update("Space toggles the scout card orientation, Enter confirms it, Esc chooses a different move.")
        else:
            hint.update(self._action_hint_text())
            hand_area.update(render_card_row(hand))

        hint.visible = True

    def _render_bot_turn(
        self, hand_area: Static, hint: Static, hand, current_player: int
    ) -> None:
        """Render the same hand area while a bot is the active actor."""
        if self.screen.config.show_bot_hands:
            hand_area.update(f"\n[dim]Player {current_player} is thinking...[/]\n" + render_card_row(hand))
        else:
            hand_area.update(
                f"\n\n[dim]Player {current_player} is thinking...[/]\n"
                f"[italic](Hand Hidden: {len(hand)} cards)[/]"
            )
        hint.visible = False

    def _render_table(self, table_area: Static, *, cards, selected_indices=None, cursor_indices=None) -> None:
        if cards:
            table_area.update(
                render_card_row(
                    list(cards),
                    selected_indices=selected_indices or set(),
                    cursor_indices=cursor_indices or set(),
                )
            )
        else:
            table_area.update("\n\n[dim](Empty Table)[/]")

    def _render_last_hand(self, hand_area: Static) -> None:
        display_state = self.screen.session.display_state if self.screen.session else None
        if display_state is None:
            hand_area.update("\n\n[dim](No Active Hand)[/]")
            return

        current_player = display_state.current_player
        hand_area.update(render_card_row(display_state.hands[current_player]))

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Highlight and enable only actions that are currently legal."""
        can_show, can_scout, can_scout_and_show = self._available_actions() if enabled else (False, False, False)
        self._configure_action_button("#btn_show", enabled=enabled and can_show)
        self._configure_action_button("#btn_scout", enabled=enabled and can_scout)
        self._configure_action_button("#btn_scout_show", enabled=enabled and can_scout_and_show)

    def _configure_action_button(self, button_id: str, *, enabled: bool) -> None:
        button = self.screen.query_one(button_id, Button)
        button.disabled = not enabled
        button.variant = "primary" if enabled else "default"

    def _available_actions(self) -> tuple[bool, bool, bool]:
        legal_moves = self.screen.session.round_controller.legal_moves if self.screen.session and self.screen.session.round_controller else []
        return (
            any(isinstance(move, ShowMove) for move in legal_moves),
            any(isinstance(move, ScoutMove) for move in legal_moves),
            any(isinstance(move, ScoutAndShowMove) for move in legal_moves),
        )

    def _action_hint_text(self) -> str:
        can_show, can_scout, can_scout_and_show = self._available_actions()
        options: list[str] = []
        if can_show:
            options.append("[bold](S)[/] to Show")
        if can_scout:
            options.append("[bold](C)[/] to Scout")
        if can_scout_and_show:
            options.append("[bold](A)[/] to Scout&Show")
        return "Choose: " + ", ".join(options) if options else "No legal actions available."
