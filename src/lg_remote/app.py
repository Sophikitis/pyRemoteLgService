from __future__ import annotations

from textual.app import App

from .config import Config
from .tv_client import TVClient


class LGRemoteApp(App):
    CSS_PATH = "lg_remote.tcss"
    TITLE = "LG Remote"

    def __init__(self, config: Config | None, force_setup: bool = False) -> None:
        super().__init__()
        self.config = config
        self.force_setup = force_setup
        self.tv_client: TVClient | None = (
            TVClient(config.tv_ip, config.client_name) if config is not None else None
        )

    def on_mount(self) -> None:
        if self.config is None or self.force_setup:
            from .screens.setup import SetupScreen

            self.push_screen(SetupScreen(initial=True))
        else:
            from .screens.remote import RemoteScreen

            self.push_screen(RemoteScreen())
