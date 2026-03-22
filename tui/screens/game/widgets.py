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

    def log_round_end(self, reason: str, scores_in: list[int], scores_out: list[int], *, round_num: int, total_rounds: int) -> None:

        delta = self._format_score_delta([out - in_ for in_, out in zip(scores_in, scores_out)])
        scores = ", ".join(f"P{i}: {score}" for i, score in enumerate(scores_out))
        self.write(f"[bold yellow]Round {round_num}/{total_rounds} over[/]: {reason} | Delta: {delta} | Scores -> {scores}")

    def log_move(self, player: int, move, *, bot_list: list, context: Optional[dict] = None) -> None:
        """Turns a resolved move into a sentence."""
        actor = _player_label(player, bot_list)
        self.write(f"{actor}: {self.describe_move(move, context or {})}")

    def describe_move(self, move, context: dict) -> str:
        # Pre-extract data to avoid repetition
        cards = self._format_cards(context.get("cards", []))
        delta = self._format_score_delta(context.get("score_delta", []))
        scouted = self._format_card(context.get("scout_card"))
        result = self._format_card(context.get("scout_result_card"))

        if isinstance(move, ShowMove):
            return f"Show {move.candidate.kind} {cards} | Delta: {delta}"

        if isinstance(move, ScoutMove):
            c = move.candidate
            return (f"Scout {scouted} (Table[{c.table_index}]) to Hand[{c.hand_insert_index}] "
                    f"as {result} | Delta: {delta}")

        if isinstance(move, ScoutAndShowMove):
            s = move.candidate.scout
            return (f"S&S: {scouted} -> {result} @ Hand[{s.hand_insert_index}], "
                    f"then show {move.candidate.show.kind} {cards} | Delta: {delta}")

        return str(move)


    def _format_card(self, card: Optional[Card]) -> str:
        """Render one card in a tiny `(active|inactive)` summary form."""
        if card is None:
            return ""
        return f"({card.active}|{card.inactive})"

    def _format_cards(self, cards) -> str:
        """Render a sequence of cards for move narration."""
        return " ".join(self._format_card(card) for card in cards)

    def _format_score_delta(self, score_delta: list[int]) -> str:
        """Only include score entries that changed on the move."""
        changes = [f"P{i} {delta:+d}" for i, delta in enumerate(score_delta) if delta]
        return ", ".join(changes) if changes else "0"


class StateOverview(Vertical):
    """Panel to display player scores, hand sizes and S&S tokens."""

    def update_summary(self, game_state, bots, current_player_idx=0) -> None:
        # Refresh
        self.remove_children()

        # extract values
        scores = game_state.scores
        hand_sizes = [len(hand) for hand in game_state.hands]
        tokens = game_state.scout_and_show_tokens

        # formatting
        for i in range(len(scores)):
            label = _player_label(i, bots)

            # Styling logic
            highlight = "active_player" if i == current_player_idx else ""
            token_markup = f"[bold green]Ready[/]" if tokens[i] else f"[bold red]Used[/]"

            row_text = (
                f"{label:<12} "  
                f"H:[bold yellow]{hand_sizes[i]:>2}[/]  "
                f"Pts:[bold cyan]{scores[i]:>3}[/]  "
                f"S&S:{token_markup}"
            )

            self.mount(Static(row_text, classes=f"score_row {highlight}"))

# TODO: extract and make helper, its also in summary builder now --> other formatting helpers?? evaluate
def _player_label(index: int, bots: list) -> str:
    """Handles seat labeling."""
    is_human = bots[index] is None

    if not is_human:
        return f"P{index} (Bot)"

    human_count = bots.count(None)
    if human_count > 1:
        return f"P{index} (Human)"

    return "YOU"