from textual.app import App

from maxscriber.tui.screens import MainScreen


class MaxScriberApp(App):
    """
    MaxScriber v0.1.0 Sci-Fi Terminal Workspace.
    """

    CSS_PATH = "styles.tcss"

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def run_tui():
    app = MaxScriberApp()
    app.run()
