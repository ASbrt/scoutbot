import random
from dataclasses import dataclass
from typing import List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Select, Input, Checkbox
from textual.containers import Vertical, Horizontal

@dataclass
class GameConfig:
    n_players: int
    seat_types: List[str]
    seed: int
    show_bot_hands: bool = False

class SetupScreen(Screen):
    """The Lobby Screen for configuring players and game settings."""
    def compose(self) -> ComposeResult:
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
                # Dynamic seat selectors will be mounted here
                pass

            with Horizontal(id="setup_footer"):
                yield Button("Back", id="back", variant="default")
                yield Button("Start Game", id="start", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        # Fixing the MountError: Don't call _rebuild_seats here directly if children use .mount()
        # Instead, Textual recommends using compose if possible, or ensuring parent is attached.
        # Since we use query_one("#seats_container"), we must ensure it exists.
        # Actually, the error was because we did row.mount(child) BEFORE row was mounted to the container.
        self._rebuild_seats(3)

    def _rebuild_seats(self, n: int) -> None:
        container = self.query_one("#seats_container", Vertical)
        container.remove_children()
        for i in range(n):
            # FIX: Use Horizontal(Static(...), Select(...)) in constructor instead of .mount() 
            # to avoid MountError when row itself isn't mounted yet.
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
        if event.select.id == "n_players":
            self._rebuild_seats(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
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
                show_bot_hands=self.query_one("#show_bot_hands", Checkbox).value
            )
            from .game.game_screen import GameScreen
            self.app.push_screen(GameScreen(config=config))
