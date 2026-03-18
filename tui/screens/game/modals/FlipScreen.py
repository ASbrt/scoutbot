"""Modal shown during the round-opening hand-orientation decision"""

from typing import List
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal

from engine.state.CardCore import Card

from ..rendering.render_cards import render_card_row


class FlipScreen(ModalScreen):
    """A modal to choose hand orientation at the start of a round."""

    def __init__(self, hand: List[Card]):
        super().__init__()
        self.hand = hand

    def compose(self) -> ComposeResult:
        """Render both hand orientations side-by-side so the choice is obvious."""
        # The controller owns the decision, this modal previews the two possible submissions before returning
        # a boolean choice
        flipped_hand = [c.flip_card() for c in self.hand]

        with Vertical(id="flip_container"):
            yield Static("CHOOSE YOUR HAND ORIENTATION", classes="header")

            with Horizontal():
                with Vertical(classes="flip_option", id="option_keep"):
                    yield Static("[bold]OPTION A (K)[/]\n(Original)")
                    yield Static(render_card_row(self.hand))
                    yield Button("Keep Original", id="keep", variant="primary")

                with Vertical(classes="flip_option", id="option_flip"):
                    yield Static("[bold]OPTION B (F)[/]\n(Flipped)")
                    yield Static(render_card_row(flipped_hand))
                    yield Button("Flip Hand", id="flip", variant="success")

            yield Static("Press K or F to choose", id="interaction_hint")

    def on_mount(self) -> None:
        """Keep keyboard shortcuts on the modal itself instead of the buttons."""
        self.query_one("#keep", Button).can_focus = False
        self.query_one("#flip", Button).can_focus = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dismiss with the boolean expected by GameScreen.handle_flip_result."""
        if event.button.id == "keep":
            self.dismiss(False)
        else:
            self.dismiss(True)

    def on_key(self, event) -> None:
        """Support quick keyboard-only confirmation for the flip choice."""
        if event.key.lower() == "k":
            self.dismiss(False)
        elif event.key.lower() == "f":
            self.dismiss(True)
