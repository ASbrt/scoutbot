from textual.widgets import Static, RichLog
from textual.containers import Vertical, Horizontal

class GameLog(RichLog):
    """A dedicated widget for game logs."""
    def on_mount(self) -> None:
        self.border_title = "GAME LOG"
        self.markup = True # Explicitly enable rich markup

class PlayerSummary(Vertical):
    """A widget to display player scores and hand sizes."""
    def update_summary(self, game_state, bots, current_player_idx):
        self.remove_children()
        for i in range(len(game_state.scores)):
            is_human = bots[i] is None
            label = "YOU" if is_human else f"P{i} (Bot)"
            
            highlight = "active_player" if i == current_player_idx else ""
            
            # Standard Textual pattern: Pass children to container constructor
            self.mount(
                Horizontal(
                    Static(f"{label:10}", classes="score_label"),
                    Static(f"Score: [bold cyan]{game_state.scores[i]}[/]", classes="score_val"),
                    Static(f"Hand: [bold yellow]{len(game_state.hands[i])}[/]", classes="hand_val"),
                    classes=f"score_row {highlight}"
                )
            )
