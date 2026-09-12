from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

BETA_WARNING = (
    "Cette application est en phase bêta.\n\n"
    "Le menu Service et les commandes protégées (IN-STOP, NVM, Factory "
    "Reset, White Balance...) peuvent avoir des conséquences irréversibles "
    "sur la TV si tu ne sais pas ce que tu fais. Ne les utilise que si tu "
    "es certain·e de leur effet."
)


class BetaWarningScreen(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(BETA_WARNING, classes="error-text")
            yield Button("J'ai compris", id="acknowledge", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "acknowledge":
            self.dismiss(None)
