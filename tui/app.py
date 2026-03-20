from textual.app import App
from .screens.home import HomeScreen

"""This is the main entry point for the TUI, it just imports styling and pushed the HomeScreen"""

class ScoutBotApp(App):
    CSS_PATH = "styles.tcss"

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


if __name__ == "__main__":
    app = ScoutBotApp()
    app.run()
