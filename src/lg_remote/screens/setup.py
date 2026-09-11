from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from ..config import DEFAULT_CLIENT_NAME, DEFAULT_CONFIG_PATH, Config, is_valid_ipv4
from ..tv_client import (
    TVClient,
    TVPairingTimeoutError,
    TVTimeoutError,
    TVUnreachableError,
)

HELP_TEXT = (
    "Trouve l'IP de la TV dans : Réglages → Tous les réglages → Général → "
    "Réseau.\nAstuce : fais une réservation DHCP sur ton routeur pour que "
    "cette IP ne change plus."
)


class SetupScreen(Screen):
    def __init__(self, *, initial: bool = False) -> None:
        super().__init__()
        self.initial = initial

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-form"):
            yield Static("Configuration de la télécommande LG", id="setup-title")
            yield Static(HELP_TEXT, classes="help-text")
            yield Input(placeholder="192.168.1.42", id="ip-input")
            yield Static("", id="setup-message")
            yield Button("Tester la connexion", id="test-button", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test-button":
            self._start_test_connection()

    def _start_test_connection(self) -> None:
        ip = self.query_one("#ip-input", Input).value.strip()
        message = self.query_one("#setup-message", Static)
        if not ip:
            message.update("[red]Entre une adresse IP.[/red]")
            return
        if not is_valid_ipv4(ip):
            message.update(f"[red]'{ip}' n'est pas une adresse IPv4 valide.[/red]")
            return
        message.update("Connexion en cours...")
        self.run_worker(self._connect(ip), exclusive=True)

    async def _connect(self, ip: str) -> None:
        message = self.query_one("#setup-message", Static)
        client = TVClient(ip, DEFAULT_CLIENT_NAME)
        try:
            await client.connect()
        except TVUnreachableError:
            message.update("[red]TV éteinte, mauvaise IP, ou hors réseau.[/red]")
            return
        except TVTimeoutError:
            message.update("En attente d'autorisation sur la TV...")
            try:
                await client.connect_with_pairing()
            except TVPairingTimeoutError:
                message.update(
                    "[red]Autorisation non reçue sur la TV. Réessaie.[/red]"
                )
                return
            except TVUnreachableError:
                message.update("[red]TV éteinte, mauvaise IP, ou hors réseau.[/red]")
                return

        message.update("[green]Connexion réussie ![/green]")
        await client.disconnect()

        config = Config(tv_ip=ip, client_name=DEFAULT_CLIENT_NAME)
        config.save(DEFAULT_CONFIG_PATH)
        self.app.config = config
        self.app.tv_client = TVClient(ip, config.client_name)

        if self.initial:
            from .remote import RemoteScreen

            self.app.switch_screen(RemoteScreen())
        else:
            self.app.pop_screen()
