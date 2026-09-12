from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App
from textual.widgets import Button, Input, Static

from lg_remote.config import Config
from lg_remote.screens.remote import RemoteScreen
from lg_remote.screens.setup import SetupScreen
from lg_remote.tv_client import (
    TVPairingRejectedError,
    TVPairingTimeoutError,
    TVTimeoutError,
    TVUnreachableError,
)


class _HostApp(App):
    CSS_PATH = "../src/lg_remote/lg_remote.tcss"

    def __init__(self, initial: bool):
        super().__init__()
        self.config = None
        self.tv_client = None
        self._initial = initial

    def on_mount(self) -> None:
        self.push_screen(SetupScreen(initial=self._initial))


async def _type_ip(pilot, ip: str) -> None:
    input_widget = pilot.app.screen.query_one("#ip-input", Input)
    input_widget.value = ip


@pytest.mark.asyncio
async def test_empty_ip_shows_inline_error_and_does_not_connect():
    app = _HostApp(initial=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#test-button")
        await pilot.pause()
        message = app.screen.query_one("#setup-message", Static)
        assert "Entre une adresse IP" in str(message.render())


@pytest.mark.asyncio
async def test_invalid_ip_shows_inline_error():
    app = _HostApp(initial=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _type_ip(pilot, "not-an-ip")
        await pilot.click("#test-button")
        await pilot.pause()
        message = app.screen.query_one("#setup-message", Static)
        assert "IPv4 valide" in str(message.render())


@pytest.mark.asyncio
async def test_successful_connect_saves_config_and_switches_to_remote(tmp_path):
    config_path = tmp_path / "config.toml"
    app = _HostApp(initial=True)
    with patch("lg_remote.screens.setup.DEFAULT_CONFIG_PATH", config_path), patch(
        "lg_remote.tv_client.TVClient.connect", AsyncMock(return_value=None)
    ), patch("lg_remote.tv_client.TVClient.disconnect", AsyncMock(return_value=None)):
        async with app.run_test() as pilot:
            await pilot.pause()
            await _type_ip(pilot, "192.168.1.42")
            await pilot.click("#test-button")
            await pilot.pause()
            await pilot.pause()
            assert isinstance(app.screen, RemoteScreen)

    assert config_path.exists()
    assert Config.load(config_path) == Config(tv_ip="192.168.1.42")


@pytest.mark.asyncio
async def test_unreachable_tv_shows_error_and_stays_on_setup():
    app = _HostApp(initial=True)
    with patch(
        "lg_remote.tv_client.TVClient.connect",
        AsyncMock(side_effect=TVUnreachableError("nope")),
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            await _type_ip(pilot, "192.168.1.42")
            await pilot.click("#test-button")
            await pilot.pause()
            await pilot.pause()
            message = app.screen.query_one("#setup-message", Static)
            assert "éteinte" in str(message.render())
            assert isinstance(app.screen, SetupScreen)


@pytest.mark.asyncio
async def test_pairing_rejected_shows_dedicated_message():
    app = _HostApp(initial=True)
    with patch(
        "lg_remote.tv_client.TVClient.connect",
        AsyncMock(side_effect=TVPairingRejectedError("refused")),
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            await _type_ip(pilot, "192.168.1.42")
            await pilot.click("#test-button")
            await pilot.pause()
            await pilot.pause()
            message = app.screen.query_one("#setup-message", Static)
            assert "refusé" in str(message.render())
            assert isinstance(app.screen, SetupScreen)


@pytest.mark.asyncio
async def test_escape_does_nothing_on_true_first_run():
    app = _HostApp(initial=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)


@pytest.mark.asyncio
async def test_escape_pops_screen_when_not_initial():
    app = _HostApp(initial=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.screen_stack) == 2
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen_stack) == 1


@pytest.mark.asyncio
async def test_pairing_timeout_shows_dedicated_message():
    app = _HostApp(initial=True)
    with patch(
        "lg_remote.tv_client.TVClient.connect",
        AsyncMock(side_effect=TVTimeoutError("slow")),
    ), patch(
        "lg_remote.tv_client.TVClient.connect_with_pairing",
        AsyncMock(side_effect=TVPairingTimeoutError("nope")),
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            await _type_ip(pilot, "192.168.1.42")
            await pilot.click("#test-button")
            await pilot.pause()
            await pilot.pause()
            message = app.screen.query_one("#setup-message", Static)
            assert "Autorisation" in str(message.render())
            assert isinstance(app.screen, SetupScreen)
