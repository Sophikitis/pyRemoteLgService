from unittest.mock import AsyncMock

import pytest
from textual.app import App
from textual.widgets import Button, Static, Switch

from lg_remote.config import Config
from lg_remote.screens.remote import RemoteScreen
from lg_remote.screens.settings import DANGER_BUTTON_IDS, SettingsScreen
from lg_remote.screens.setup import SetupScreen


class _HostApp(App):
    CSS_PATH = "../src/lg_remote/lg_remote.tcss"

    def __init__(self, tv_client):
        super().__init__()
        self.config = Config(tv_ip="192.168.1.42")
        self.tv_client = tv_client

    def on_mount(self) -> None:
        self.push_screen(RemoteScreen())


@pytest.mark.asyncio
async def test_pressing_c_opens_settings_screen():
    app = _HostApp(tv_client=AsyncMock())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)


@pytest.mark.asyncio
async def test_escape_pops_back_to_remote_screen():
    app = _HostApp(tv_client=AsyncMock())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, RemoteScreen)


@pytest.mark.asyncio
async def test_reconfigure_button_pushes_setup_screen_not_initial():
    app = _HostApp(tv_client=AsyncMock())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()
        await pilot.click("#reconfigure-button")
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)
        assert app.screen.initial is False


@pytest.mark.asyncio
async def test_danger_buttons_start_disabled():
    app = _HostApp(tv_client=AsyncMock())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()
        for button_id in DANGER_BUTTON_IDS:
            button = app.screen.query_one(f"#{button_id}", Button)
            assert button.disabled is True


@pytest.mark.asyncio
async def test_toggling_danger_switch_asks_for_confirmation():
    app = _HostApp(tv_client=AsyncMock())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()
        switch = app.screen.query_one("#danger-toggle", Switch)
        switch.toggle()
        await pilot.pause()
        assert app.screen.query_one("#confirm-box")


@pytest.mark.asyncio
async def test_confirming_danger_toggle_reveals_zone_but_buttons_stay_disabled():
    app = _HostApp(tv_client=AsyncMock())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()
        switch = app.screen.query_one("#danger-toggle", Switch)
        switch.toggle()
        await pilot.pause()
        await pilot.click("#confirm")
        await pilot.pause()
        danger_zone = app.screen.query_one("#danger-zone")
        assert danger_zone.display is True
        for button_id in DANGER_BUTTON_IDS:
            button = app.screen.query_one(f"#{button_id}", Button)
            assert button.disabled is True


@pytest.mark.asyncio
async def test_log_panel_shows_recent_commands():
    tv_client = AsyncMock()
    tv_client.command_log = ["button HOME", "volume_up"]
    app = _HostApp(tv_client=tv_client)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()
        log_panel = app.screen.query_one("#log-panel", Static)
        rendered = str(log_panel.render())
        assert "button HOME" in rendered
        assert "volume_up" in rendered
