from __future__ import annotations

from textual.app import App

from .config import Config
from .tv_client import TVClient


class LGRemoteApp(App):
    CSS_PATH = "lg_remote.tcss"
    TITLE = "LG Remote"

    def __init__(self, config: Config | None, force_setup: bool = False) -> None:
        super().__init__()
        self.theme = "catppuccin-mocha"
        self.config = config
        self.force_setup = force_setup
        self.tv_client: TVClient | None = (
            TVClient(config.tv_ip, config.client_name) if config is not None else None
        )

    def on_mount(self) -> None:
        if self.config is None:
            from .screens.setup import SetupScreen

            self.push_screen(SetupScreen(initial=True))
            return

        from .screens.remote import RemoteScreen

        self.push_screen(RemoteScreen())
        if self.force_setup:
            # A RemoteScreen already exists underneath — reuse the
            # normal "reconfigure" flow (initial=False) instead of the
            # true-first-run one, so escape and a successful reconnect
            # both fall back to it instead of an empty default screen.
            from .screens.setup import SetupScreen

            self.push_screen(SetupScreen(initial=False))
