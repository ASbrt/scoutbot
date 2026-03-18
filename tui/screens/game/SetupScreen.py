import random
from dataclasses import dataclass
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Select, Input, Checkbox
from textual.containers import Vertical, Horizontal

"""Lobby Screen for Game setup"""

# TODO: If there is time left, adapt so multiple people can play at the same time

@dataclass
class GameConfig:
    """Configuration payload passed from the lobby into GameScreen."""

    n_players: int
    seat_types: list[str]
    seed: int
    show_bot_hands: bool = False


class SetupScreen(Screen):
    """The Lobby Screen for configuring players and game settings."""

    def compose(self) -> ComposeResult:
        """Render the configurable fields that define one game session."""
        yield Header()
        yield Static("LOBBY SETUP", id="setup_title")
        with Vertical(id="setup_body"):
            with Horizontal(classes="config_row"):
                yield Static("Players:  ", classes="label")
                yield Select(
                    options=[("3", 3), ("4", 4), ("5", 5)],
                    value=3,
                    id="n_players"
                )
            
            with Horizontal(classes="config_row"):
                yield Static("Seed:     ", classes="label")
                yield Input(placeholder="optional", id="seed")

            with Horizontal(classes="config_row"):
                yield Static("Bot Hands: ", classes="label")
                yield Checkbox("Show", value=False, id="show_bot_hands")

            with Vertical(id="seats_container"):
                pass

            with Horizontal(id="setup_footer"):
                yield Button("Back", id="back", variant="default")
                yield Button("Start Game", id="start", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        """Populate the initial seat list once the container exists in the DOM."""
        self._rebuild_seats(3)

    def _rebuild_seats(self, n: int) -> None:
        """Regenerate the seat selectors after the player-count changes."""
        container = self.query_one("#seats_container", Vertical)
        container.remove_children()
        for i in range(n):
            # Build the entire row in one constructor call so Textual can mount a
            # ready-made subtree instead of piecemeal child widgets.
            row = Horizontal(
                Static(f"Player {i}: ", classes="seat_label"),
                Select(
                    options=[("Human", "human"), ("Random Bot", "random")],
                    value="human" if i == 0 else "random",
                    id=f"seat_{i}"
                ),
                classes="seat_row"
            )
            container.mount(row)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Resize the seat selector list when the player count changes."""
        if event.select.id == "n_players":
            self._rebuild_seats(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Either leave the lobby or assemble a GameConfig and launch gameplay."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "start":
            n_players = self.query_one("#n_players", Select).value
            seed_text = self.query_one("#seed", Input).value.strip()
            seed = int(seed_text) if seed_text else random.randrange(10**9)

            seat_types = []
            for i in range(n_players):
                seat_types.append(self.query_one(f"#seat_{i}", Select).value)

            config = GameConfig(
                n_players=n_players,
                seat_types=seat_types,
                seed=seed,
                show_bot_hands=self.query_one("#show_bot_hands", Checkbox).value,
            )
            from .GameScreen import GameScreen

            self.app.push_screen(GameScreen(config=config))
