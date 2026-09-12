from unittest.mock import AsyncMock, patch

import pytest

from lg_remote.app import LGRemoteApp
from lg_remote.config import Config
from lg_remote.screens.beta import BetaWarningScreen
from lg_remote.screens.remote import RemoteScreen
from lg_remote.screens.setup import SetupScreen
from lg_remote.tv_client import TVUnreachableError


async def _dismiss_beta_warning(pilot) -> None:
    await pilot.click("#acknowledge")
    await pilot.pause()


@pytest.mark.asyncio
async def test_beta_warning_is_shown_before_setup_or_remote_screen():
    app = LGRemoteApp(config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, BetaWarningScreen)


@pytest.mark.asyncio
async def test_shows_setup_screen_when_no_config():
    app = LGRemoteApp(config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _dismiss_beta_warning(pilot)
        assert isinstance(app.screen, SetupScreen)
        assert app.screen.initial is True


@pytest.mark.asyncio
async def test_shows_remote_screen_when_config_present():
    app = LGRemoteApp(config=Config(tv_ip="192.168.1.50"))
    with patch(
        "lg_remote.tv_client.TVClient.connect",
        AsyncMock(side_effect=TVUnreachableError("fake, no real TV in tests")),
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            await _dismiss_beta_warning(pilot)
            assert isinstance(app.screen, RemoteScreen)


@pytest.mark.asyncio
async def test_force_setup_overrides_existing_config():
    app = LGRemoteApp(config=Config(tv_ip="192.168.1.50"), force_setup=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _dismiss_beta_warning(pilot)
        assert isinstance(app.screen, SetupScreen)
        # Not a true first run: a RemoteScreen already exists underneath,
        # so escape (and a successful reconnect) can fall back to it.
        assert app.screen.initial is False


@pytest.mark.asyncio
async def test_force_setup_escape_falls_back_to_remote_screen():
    app = LGRemoteApp(config=Config(tv_ip="192.168.1.50"), force_setup=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _dismiss_beta_warning(pilot)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, RemoteScreen)


@pytest.mark.asyncio
async def test_true_first_run_escape_does_nothing():
    app = LGRemoteApp(config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _dismiss_beta_warning(pilot)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)


def test_tv_client_is_none_without_config():
    app = LGRemoteApp(config=None)
    assert app.tv_client is None


def test_tv_client_is_built_from_config():
    app = LGRemoteApp(config=Config(tv_ip="192.168.1.50", client_name="my-client"))
    assert app.tv_client is not None
    assert app.tv_client.ip == "192.168.1.50"
    assert app.tv_client.client_name == "my-client"
