from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Static

from ..tv_client import TVConnectionError

WARNING_TEXT = (
    "Ces réglages peuvent affecter le calibrage de l'écran.\n"
    "Continuer uniquement si tu sais ce que tu fais."
)


class ServiceConfirmScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(WARNING_TEXT, classes="error-text")
            with Horizontal():
                yield Button("Annuler", id="cancel")
                yield Button("Continuer", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class ServiceScreen(Screen):
    BINDINGS = [Binding("escape", "pop_screen", "Retour")]

    def compose(self) -> ComposeResult:
        with Vertical(id="service-form"):
            yield Static(WARNING_TEXT, classes="error-text")
            yield Button("IN-START", id="in-start", variant="primary")
            yield Button("EZ-ADJUST", id="ez-adjust", variant="primary")
            yield Button("EXIT (sortir du menu)", id="service-exit", variant="success")
        yield Footer()

    def action_pop_screen(self) -> None:
        # Screen doesn't inherit App's action_pop_screen for its own
        # BINDINGS dispatch — without this, the "escape" binding above
        # silently does nothing (verified against the installed Textual).
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "in-start":
            self.run_worker(self._send("open_in_start"), group="tv-command")
        elif event.button.id == "ez-adjust":
            self.run_worker(self._send("open_ez_adjust"), group="tv-command")
        elif event.button.id == "service-exit":
            self.run_worker(self._send_exit(), group="tv-command")

    async def _send(self, method_name: str) -> None:
        tv_client = self.app.tv_client
        if tv_client is None:
            self.app.notify("TV injoignable", severity="warning")
            return
        try:
            await getattr(tv_client, method_name)()
        except TVConnectionError:
            self.app.notify("TV injoignable", severity="error")
            return
        self.app.notify(method_name.replace("_", " "), timeout=1.5)

    async def _send_exit(self) -> None:
        # EXIT means both things: tell the TV to close its on-screen
        # factory menu, and leave this screen back to the main remote.
        await self._send("exit")
        self.app.pop_screen()
