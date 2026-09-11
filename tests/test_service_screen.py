from unittest.mock import AsyncMock

import pytest
from textual.app import App
from textual.css.query import NoMatches

from lg_remote.screens.remote import RemoteScreen
from lg_remote.screens.service import ServiceScreen


class _HostApp(App):
    CSS_PATH = "../src/lg_remote/lg_remote.tcss"

    def __init__(self, tv_client):
        super().__init__()
        self.config = None
        self.tv_client = tv_client

    def on_mount(self) -> None:
        self.push_screen(RemoteScreen())


@pytest.mark.asyncio
async def test_pressing_s_shows_confirmation_then_service_screen_on_confirm():
    tv_client = AsyncMock()
    app = _HostApp(tv_client=tv_client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        await pilot.click("#confirm")
        await pilot.pause()
        assert isinstance(app.screen, ServiceScreen)


@pytest.mark.asyncio
async def test_pressing_s_then_cancel_does_not_open_service_screen():
    tv_client = AsyncMock()
    app = _HostApp(tv_client=tv_client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, ServiceScreen)


@pytest.mark.asyncio
async def test_in_start_button_calls_tv_client_open_in_start():
    tv_client = AsyncMock()
    app = _HostApp(tv_client=tv_client)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(ServiceScreen())
        await pilot.pause()
        await pilot.click("#in-start")
        await pilot.pause()
    tv_client.open_in_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_ez_adjust_button_calls_tv_client_open_ez_adjust():
    tv_client = AsyncMock()
    app = _HostApp(tv_client=tv_client)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(ServiceScreen())
        await pilot.pause()
        await pilot.click("#ez-adjust")
        await pilot.pause()
    tv_client.open_ez_adjust.assert_awaited_once()


@pytest.mark.asyncio
async def test_exit_button_calls_tv_client_exit_never_in_stop():
    tv_client = AsyncMock()
    app = _HostApp(tv_client=tv_client)
    async with app.run_test() as pilot:
        await pilot.pause()
        service_screen = ServiceScreen()
        app.push_screen(service_screen)
        await pilot.pause()
        with pytest.raises(NoMatches):
            service_screen.query_one("#in-stop")
        await pilot.click("#service-exit")
        await pilot.pause()
        assert isinstance(app.screen, RemoteScreen)
    tv_client.exit.assert_awaited_once()


@pytest.mark.asyncio
async def test_escape_pops_back_to_remote_screen():
    tv_client = AsyncMock()
    app = _HostApp(tv_client=tv_client)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(ServiceScreen())
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, RemoteScreen)
