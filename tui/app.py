from textual.app import App
from .screens.home import HomeScreen

class ScoutBotApp(App):
    """The main ScoutBot TUI Application."""
    CSS_PATH = "styles.tcss"
    
    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

if __name__ == "__main__":
    app = ScoutBotApp()
    app.run()