from textual.app import App
from .screens.home import HomeScreen

"""This is the main entry point for the TUI"""

class ScoutBotApp(App):
    """The main ScoutBot TUI Application."""
    CSS_PATH = "styles.tcss"

    def on_mount(self) -> None:
        """Boot directly into the home screen once Textual is ready."""
        self.push_screen(HomeScreen())


if __name__ == "__main__":
    app = ScoutBotApp()
    app.run()
