from typing import List
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal

from engine.state.simulation_core import Card
from ...render_cards import render_card_row

class FlipScreen(ModalScreen):
    """A modal to choose hand orientation at the start of a round."""
    def __init__(self, hand: List[Card]):
        super().__init__()
        self.hand = hand

    def compose(self) -> ComposeResult:
        # Create a flipped version of the hand for preview
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
        # Ensure buttons don't steal Enter
        self.query_one("#keep", Button).can_focus = False
        self.query_one("#flip", Button).can_focus = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "keep":
            self.dismiss(False)
        else:
            self.dismiss(True)

    def on_key(self, event) -> None:
        if event.key.lower() == "k":
            self.dismiss(False)
        elif event.key.lower() == "f":
            self.dismiss(True)
