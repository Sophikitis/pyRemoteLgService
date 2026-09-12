from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from ..tv_client import TVConnectionError

RECONNECT_INTERVAL_SECONDS = 5

BUTTON_TO_METHOD = {
    "power": "power",
    "home": "home",
    "back": "back",
    "exit": "exit",
    "nav-up": "nav_up",
    "nav-down": "nav_down",
    "nav-left": "nav_left",
    "nav-right": "nav_right",
    "dpad-ok": "ok",
    "vol-up": "volume_up",
    "vol-down": "volume_down",
    "mute": "mute",
    "ch-up": "channel_up",
    "ch-down": "channel_down",
    "info": "info",
    "input-source": "input_source",
    "netflix": "netflix",
}


class RemoteScreen(Screen):
    # Without this, Textual auto-focuses the first focusable widget in
    # compose() — the Power button — and a focused Button consumes Enter
    # before this screen's BINDINGS ever see it, so Enter powers off the
    # TV instead of sending OK (verified against the installed Textual).
    AUTO_FOCUS = "#dpad-ok"

    BINDINGS = [
        Binding("up", "press_button('nav-up')", "Haut", show=False),
        Binding("down", "press_button('nav-down')", "Bas", show=False),
        Binding("left", "press_button('nav-left')", "Gauche", show=False),
        Binding("right", "press_button('nav-right')", "Droite", show=False),
        Binding("enter", "press_button('dpad-ok')", "OK", show=False),
        Binding("plus", "press_button('vol-up')", "Volume +", show=False),
        Binding("minus", "press_button('vol-down')", "Volume -", show=False),
        Binding("m", "press_button('mute')", "Muet", show=False),
        Binding("s", "open_service", "Service"),
        Binding("c", "open_settings", "Réglages"),
    ]

    connected: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="status-bar")
        with Horizontal(id="top-row"):
            yield Button("Power", id="power", variant="error")
            yield Button("Home", id="home")
            yield Button("Back", id="back")
            yield Button("Exit", id="exit")
        with Vertical(id="dpad"):
            yield Button("▲", id="nav-up")
            with Horizontal():
                yield Button("◀", id="nav-left")
                yield Button("OK", id="dpad-ok", variant="success")
                yield Button("▶", id="nav-right")
            yield Button("▼", id="nav-down")
        with Horizontal(id="vol-channel-row"):
            with Vertical():
                yield Button("Vol +", id="vol-up")
                yield Button("Mute", id="mute")
                yield Button("Vol -", id="vol-down")
            with Vertical():
                yield Button("Ch +", id="ch-up")
                yield Button("Info", id="info")
                yield Button("Ch -", id="ch-down")
        with Horizontal(id="quick-apps-row"):
            yield Button("Netflix", id="netflix")
            yield Button("Source", id="input-source")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._connect_and_watch(), exclusive=True, group="connection")

    async def _connect_and_watch(self) -> None:
        last_client = None
        while True:
            tv_client = self.app.tv_client
            if tv_client is None:
                self.connected = False
                return
            if tv_client is not last_client:
                # app.tv_client was swapped out from under us (a
                # reconfigure elsewhere replaced it with a fresh, not-yet-
                # connected client) — forget any stale "connected" state
                # so we actually attempt the new client instead of
                # trusting a flag that describes the old one.
                self.connected = False
                last_client = tv_client
            if not self.connected:
                try:
                    await tv_client.connect()
                except TVConnectionError:
                    self.connected = False
                else:
                    self.connected = True
            await asyncio.sleep(RECONNECT_INTERVAL_SECONDS)

    def watch_connected(self, connected: bool) -> None:
        status = self.query_one("#status-bar", Static)
        config = self.app.config
        ip = config.tv_ip if config else "?"
        if connected:
            status.update(f"[green]● Connecté[/green] — {ip}")
            status.remove_class("-disconnected")
            status.add_class("-connected")
        else:
            status.update(
                f"[red]● TV injoignable[/red] — {ip} — appuie sur 'c' pour reconfigurer"
            )
            status.remove_class("-connected")
            status.add_class("-disconnected")

    def action_press_button(self, button_id: str) -> None:
        self._dispatch(button_id)

    def action_open_service(self) -> None:
        from .service import ServiceConfirmScreen, ServiceScreen

        def handle_confirmed(confirmed: bool | None) -> None:
            if confirmed:
                self.app.push_screen(ServiceScreen())

        self.app.push_screen(ServiceConfirmScreen(), handle_confirmed)

    def action_open_settings(self) -> None:
        from .settings import SettingsScreen

        self.app.push_screen(SettingsScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id:
            self._dispatch(event.button.id)

    def _dispatch(self, button_id: str) -> None:
        method_name = BUTTON_TO_METHOD.get(button_id)
        if method_name is None:
            return
        self.run_worker(self._send(method_name), group="tv-command")

    async def _send(self, method_name: str) -> None:
        tv_client = self.app.tv_client
        if tv_client is None or not self.connected:
            self.app.notify("TV injoignable", severity="warning")
            return
        try:
            await getattr(tv_client, method_name)()
        except TVConnectionError:
            self.connected = False
            self.app.notify("TV injoignable", severity="error")
            return
        self.app.notify(method_name.replace("_", " "), timeout=1.5)
