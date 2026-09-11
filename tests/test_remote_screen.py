from unittest.mock import AsyncMock

import pytest
from textual.app import App
from textual.widgets import Static

from lg_remote.screens.remote import RemoteScreen
from lg_remote.tv_client import TVConnectionError


class _HostApp(App):
    """Minimal app just to mount RemoteScreen in isolation."""

    CSS_PATH = "../src/lg_remote/lg_remote.tcss"

    def __init__(self, tv_client, config):
        super().__init__()
        self.tv_client = tv_client
        self.config = config

    def on_mount(self) -> None:
        self.push_screen(RemoteScreen())


def _fake_tv_client(connect_side_effect=None):
    tv_client = AsyncMock()
    tv_client.connect.side_effect = connect_side_effect
    return tv_client


@pytest.mark.asyncio
async def test_status_bar_shows_connected_after_successful_connect():
    app = _HostApp(tv_client=_fake_tv_client(), config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.screen.query_one("#status-bar", Static)
        assert "Connecté" in str(status.render())


@pytest.mark.asyncio
async def test_status_bar_shows_unreachable_when_connect_fails():
    app = _HostApp(
        tv_client=_fake_tv_client(connect_side_effect=TVConnectionError("nope")),
        config=None,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.screen.query_one("#status-bar", Static)
        rendered = str(status.render())
        assert "injoignable" in rendered
        assert "'c'" in rendered


@pytest.mark.asyncio
async def test_pressing_home_button_calls_tv_client_home():
    tv_client = _fake_tv_client()
    app = _HostApp(tv_client=tv_client, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home")
        await pilot.pause()
    tv_client.home.assert_awaited_once()


@pytest.mark.asyncio
async def test_pressing_vol_up_calls_tv_client_volume_up():
    tv_client = _fake_tv_client()
    app = _HostApp(tv_client=tv_client, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#vol-up")
        await pilot.pause()
    tv_client.volume_up.assert_awaited_once()


@pytest.mark.asyncio
async def test_arrow_key_binding_sends_nav_up():
    tv_client = _fake_tv_client()
    app = _HostApp(tv_client=tv_client, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
    tv_client.nav_up.assert_awaited_once()


@pytest.mark.asyncio
async def test_pressing_button_while_disconnected_notifies_instead_of_sending():
    tv_client = _fake_tv_client(connect_side_effect=TVConnectionError("nope"))
    app = _HostApp(tv_client=tv_client, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#home")
        await pilot.pause()
    tv_client.home.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_tv_client_configured_leaves_status_disconnected():
    app = _HostApp(tv_client=None, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.screen.query_one("#status-bar", Static)
        assert "injoignable" in str(status.render())
