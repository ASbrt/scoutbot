"""Home screen for entering the playable parts of the TUI."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Vertical


class HomeScreen(Screen):
    def compose(self) -> ComposeResult:
        """Builds some buttons for navigation, very basic layout"""
        yield Header()
        yield Static("SCOUT BOT", id="main_title")
        with Vertical(id="menu_container"):
            yield Button("Play Game", id="nav_play", variant="primary")
            yield Button("Training Data (WIP)", id="nav_data", disabled=True)
            yield Button("Tournaments (WIP)", id="nav_tourney", disabled=True)
            yield Button("Quit", id="nav_quit", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route button presses to the appropriate next screen or action."""
        if event.button.id == "nav_play":
            from tui.screens.game.SetupScreen import SetupScreen

            self.app.push_screen(SetupScreen())
        elif event.button.id == "nav_quit":
            self.app.exit()
        elif event.button.id == "nav_data":
            # These routes are intentionally left visible so the UI roadmap is
            # discoverable, even though the underlying screens do not exist yet.
            self.notify("Training Data view is not yet implemented.")
        elif event.button.id == "nav_tourney":
            self.notify("Tournaments view is not yet implemented.")
