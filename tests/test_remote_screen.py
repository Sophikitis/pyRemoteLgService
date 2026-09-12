import asyncio
from unittest.mock import AsyncMock

import pytest
from textual.app import App
from textual.widgets import Static

from lg_remote.config import Config
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
async def test_enter_key_sends_ok_not_power():
    tv_client = _fake_tv_client()
    app = _HostApp(tv_client=tv_client, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    tv_client.ok.assert_awaited_once()
    tv_client.power.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconnect_loop_picks_up_a_swapped_in_tv_client(monkeypatch):
    monkeypatch.setattr(
        "lg_remote.screens.remote.RECONNECT_INTERVAL_SECONDS", 0.01
    )
    old_client = _fake_tv_client()
    app = _HostApp(tv_client=old_client, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.screen.query_one("#status-bar", Static)
        assert "Connecté" in str(status.render())

        new_client = _fake_tv_client()
        app.tv_client = new_client
        await asyncio.sleep(0.05)
        await pilot.pause()

    new_client.connect.assert_awaited()


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
async def test_dpad_up_and_down_are_centered_over_ok_button():
    app = _HostApp(tv_client=_fake_tv_client(), config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        ok = app.screen.query_one("#dpad-ok")
        up = app.screen.query_one("#nav-up")
        down = app.screen.query_one("#nav-down")
        ok_center = ok.region.x + ok.region.width / 2
        up_center = up.region.x + up.region.width / 2
        down_center = down.region.x + down.region.width / 2
        assert up_center == pytest.approx(ok_center, abs=1)
        assert down_center == pytest.approx(ok_center, abs=1)


@pytest.mark.asyncio
async def test_no_tv_client_configured_leaves_status_disconnected():
    app = _HostApp(tv_client=None, config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        status = app.screen.query_one("#status-bar", Static)
        assert "injoignable" in str(status.render())


@pytest.mark.asyncio
async def test_vol_down_and_ch_down_are_not_clipped_by_their_column():
    app = _HostApp(tv_client=_fake_tv_client(), config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        for button_id, column_id in (
            ("#vol-down", "#vol-up"),
            ("#ch-down", "#ch-up"),
        ):
            button = app.screen.query_one(button_id)
            column = app.screen.query_one(column_id).parent
            # The bottom button's box must be fully inside its column's
            # own box — a column too short for its 3 buttons clips the
            # last one out of view instead of raising an error.
            assert button.region.y + button.region.height <= (
                column.region.y + column.region.height
            )


@pytest.mark.asyncio
async def test_keypad_shown_by_default_with_no_config():
    app = _HostApp(tv_client=_fake_tv_client(), config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        keypad = app.screen.query_one("#keypad")
        assert keypad.display is True


@pytest.mark.asyncio
async def test_keypad_hidden_when_config_disables_numbers():
    config = Config(tv_ip="192.168.1.42", numbers_enabled=False)
    app = _HostApp(tv_client=_fake_tv_client(), config=config)
    async with app.run_test() as pilot:
        await pilot.pause()
        keypad = app.screen.query_one("#keypad")
        assert keypad.display is False


@pytest.mark.asyncio
async def test_keypad_hides_live_after_disabling_numbers_in_settings(tmp_path):
    from unittest.mock import patch

    from lg_remote.screens.settings import SettingsScreen

    config = Config(tv_ip="192.168.1.42")
    app = _HostApp(tv_client=_fake_tv_client(), config=config)
    with patch(
        "lg_remote.screens.settings.DEFAULT_CONFIG_PATH", tmp_path / "config.toml"
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            app.push_screen(SettingsScreen())
            await pilot.pause()
            switch = app.screen.query_one("#numbers-toggle")
            switch.toggle()
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, RemoteScreen)
            assert app.screen.query_one("#keypad").display is False


@pytest.mark.asyncio
async def test_pressing_num_5_sends_digit_5_to_tv_client():
    tv_client = _fake_tv_client()
    app = _HostApp(tv_client=tv_client, config=None)
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        await pilot.click("#num-5")
        await pilot.pause()
    tv_client.number.assert_awaited_once_with("5")
