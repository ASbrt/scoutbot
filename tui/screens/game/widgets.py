"""GameLog and State Overview widgets for logs and player summaries in the gameplay screen."""

from typing import Optional
from engine.state.CardCore import Card
from engine.state.GameState import ScoutAndShowMove, ScoutMove, ShowMove
from textual.containers import Vertical
from textual.widgets import RichLog, Static


class GameLog(RichLog):
    """
    Widget for game logs. Bots act quickly sometimes, so this is for following the play-by play and logging
    any errors (e.g. invalid move selection)
    """

    def on_mount(self) -> None:
        self.border_title = "GAME LOG"
        self.markup = True

    def log_info(self, message: str) -> None:
        self.write(message)

    def log_error(self, message: str) -> None:
        self.write(f"[bold red]{message}[/]")

    def log_phase(self, label: str) -> None:
        """Write a visual separator for major game phases."""
        self.write(f"[bold magenta]{label}[/]")

    def log_round_start(self, round_num: int, total_rounds: int, n_players: int) -> None:
        self.write(f"[bold green]Round {round_num}/{total_rounds}[/] begins with {n_players} players.")

    def log_round_end(
        self, reason: str, scores_in: list[int], scores_out: list[int], *, round_num: int, total_rounds: int) -> None:
        delta = self._format_score_delta([out - in_ for in_, out in zip(scores_in, scores_out)])
        scores = ", ".join(f"P{i}: {score}" for i, score in enumerate(scores_out))
        self.write(f"[bold yellow]Round {round_num}/{total_rounds} over[/]: {reason} | Delta: {delta} | Scores -> {scores}")

    def log_move(self, player: int, move, *, is_bot: bool, context: Optional[dict] = None) -> None:
        """Render one resolved move into a sentence."""
        actor = f"P{player} (Bot)" if is_bot else "You"
        self.write(f"{actor}: {self._describe_move(move, context or {})}")

    def _describe_move(self, move, context: dict) -> str:
        """Translate typed move objects into readable prose for the side log."""
        if isinstance(move, ShowMove):
            candidate = move.candidate
            cards = self._format_cards(context.get("cards"))
            delta = self._format_score_delta(context.get("score_delta", []))
            return f"Show {candidate.kind} {cards} | Score delta: {delta}"
        if isinstance(move, ScoutMove):
            candidate = move.candidate
            scouted = self._format_card(context.get("scout_card"))
            result = self._format_card(context.get("scout_result_card"))
            delta = self._format_score_delta(context.get("score_delta", []))
            return (
                f"Scout {scouted} from table[{candidate.table_index}] to hand[{candidate.hand_insert_index}] "
                f"as {result} | Score delta: {delta}"
            )
        if isinstance(move, ScoutAndShowMove):
            scout = move.candidate.scout
            show = move.candidate.show
            scouted = self._format_card(context.get("scout_card"))
            result = self._format_card(context.get("scout_result_card"))
            cards = self._format_cards(context.get("cards"))
            delta = self._format_score_delta(context.get("score_delta", []))
            return (
                f"Scout & Show: {scouted} -> {result} at hand[{scout.hand_insert_index}], "
                f"then show {show.kind} {cards} | Score delta: {delta}"
            )
        return str(move)

    def _format_card(self, card: Optional[Card]) -> str:
        """Render one card in a tiny `(active|inactive)` summary form."""
        if card is None:
            return "(?)"
        return f"({card.active}|{card.inactive})"

    def _format_cards(self, cards) -> str:
        """Render a sequence of cards for move narration."""
        if not cards:
            return "(no cards)"
        return " ".join(self._format_card(card) for card in cards)

    def _format_score_delta(self, score_delta: list[int]) -> str:
        """Only include score entries that changed on the move."""
        changes = [f"P{i} {delta:+d}" for i, delta in enumerate(score_delta) if delta]
        return ", ".join(changes) if changes else "no score change"


class StateOverview(Vertical):
    """Panel to display player scores, hand sizes and S&S tokens."""

    def update_summary(self, game_state, bots, current_player_idx=0) -> None:
        """Render player overview from GameState."""

        # Refresh
        self.remove_children()

        # extract values
        scores = game_state.scores
        hand_sizes = [len(hand) for hand in game_state.hands]
        tokens = game_state.scout_and_show_tokens

        # formatting
        for i in range(len(scores)):
            is_human = bots[i] is None
            label = "YOU" if is_human else f"P{i} (Bot)"
            highlight = "active_player" if i == current_player_idx else ""

            token_val = tokens[i]
            token_text = "Ready" if token_val else "Used"
            token_markup = (f"[bold green]{token_text}[/]" if token_val else f"[bold red]{token_text}[/]")

            row_text = (
                f"{label:<8} "
                f"H:[bold yellow]{hand_sizes[i]}[/]  "
                f"Pts:[bold cyan]{scores[i]}[/]  "
                f"S&S:{token_markup}"
            )

            self.mount(Static(row_text, classes=f"score_row {highlight}"))
