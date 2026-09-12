from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Static, Switch

DANGER_WARNING = (
    "Ces commandes ne sont pas vérifiées contre du matériel réel et peuvent "
    "dérégler ou endommager la dalle. Elles restent désactivées : le "
    "payload exact n'a pas été confirmé contre bscpylgtv."
)

DANGER_BUTTON_IDS = (
    "danger-in-stop",
    "danger-nvm",
    "danger-factory-reset",
    "danger-white-balance",
)

DANGER_LABELS = {
    "danger-in-stop": "IN-STOP",
    "danger-nvm": "NVM",
    "danger-factory-reset": "Factory Reset",
    "danger-white-balance": "White Balance",
}


class DangerConfirmScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(DANGER_WARNING, classes="error-text")
            with Horizontal():
                yield Button("Annuler", id="cancel")
                yield Button("Activer quand même", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class SettingsScreen(Screen):
    BINDINGS = [Binding("escape", "pop_screen", "Retour")]

    def action_pop_screen(self) -> None:
        # Screen doesn't inherit App's action_pop_screen for its own
        # BINDINGS dispatch — without this, the "escape" binding above
        # silently does nothing (verified against the installed Textual;
        # see the same fix and its comment in ServiceScreen, Task 8).
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-form"):
            yield Static("Réglages", id="settings-title")
            config = self.app.config
            yield Static(
                f"IP actuelle : {config.tv_ip if config else 'non configurée'}",
                id="current-ip",
            )
            yield Button("Reconfigurer l'IP", id="reconfigure-button", variant="primary")
            yield Static(
                "Commandes protégées (IN-STOP, NVM, Factory Reset, White Balance)",
                classes="section-title",
            )
            yield Switch(value=False, id="danger-toggle")
            with Vertical(id="danger-zone", classes="danger-zone"):
                for button_id in DANGER_BUTTON_IDS:
                    yield Button(
                        DANGER_LABELS[button_id],
                        id=button_id,
                        disabled=True,
                        variant="error",
                    )
                yield Static(DANGER_WARNING, classes="help-text")
            yield Static("Journal des commandes", classes="section-title")
            yield Static("", id="log-panel")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#danger-zone").display = False
        self._refresh_log()

    def on_screen_resume(self) -> None:
        # Reached after popping back from Reconfigurer l'IP — the IP and
        # the client the log reads from may both have changed underneath
        # this screen, which was never recomposed to know that.
        self._refresh_current_ip()
        self._refresh_log()

    def _refresh_current_ip(self) -> None:
        config = self.app.config
        self.query_one("#current-ip", Static).update(
            f"IP actuelle : {config.tv_ip if config else 'non configurée'}"
        )

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id != "danger-toggle":
            return
        if event.value:
            def handle_confirmed(confirmed: bool | None) -> None:
                self.query_one("#danger-zone").display = bool(confirmed)
                if not confirmed:
                    event.switch.value = False

            self.app.push_screen(DangerConfirmScreen(), handle_confirmed)
        else:
            self.query_one("#danger-zone").display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reconfigure-button":
            from .setup import SetupScreen

            self.app.push_screen(SetupScreen(initial=False))

    def _refresh_log(self) -> None:
        tv_client = self.app.tv_client
        lines = tv_client.command_log if tv_client else []
        self.query_one("#log-panel", Static).update("\n".join(lines[-10:]) or "(vide)")
