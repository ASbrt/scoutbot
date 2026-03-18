"""Small reusable modal for game summaries."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class SummaryModal(ModalScreen[None]):
    """Reusable modal for round-end and game-end summaries."""

    def __init__(self, *, title: str, body: str, button_label: str) -> None:
        super().__init__()
        self.title = title
        self.body = body
        self.button_label = button_label

    def compose(self) -> ComposeResult:
        """Render the summary text and a single acknowledgment button."""
        with Vertical(id="summary_container"):
            yield Static(self.title, classes="header")
            yield Static(self.body, id="summary_body")
            yield Button(self.button_label, id="summary_confirm", variant="primary")

    def on_mount(self) -> None:
        """Leave focus on the modal so Enter/Escape dismiss consistently."""
        self.query_one("#summary_confirm", Button).can_focus = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Close once the user confirms the summary."""
        if event.button.id == "summary_confirm":
            self.dismiss(None)

    def on_key(self, event) -> None:
        """Accept the common "continue" keys for convenience."""
        if event.key.lower() in {"enter", "escape"}:
            self.dismiss(None)
