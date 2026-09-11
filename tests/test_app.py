from unittest.mock import AsyncMock, patch

import pytest

from lg_remote.app import LGRemoteApp
from lg_remote.config import Config
from lg_remote.screens.remote import RemoteScreen
from lg_remote.screens.setup import SetupScreen
from lg_remote.tv_client import TVUnreachableError


@pytest.mark.asyncio
async def test_shows_setup_screen_when_no_config():
    app = LGRemoteApp(config=None)
    async with app.run_test() as pilot:
        await pilot.pause()
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
            assert isinstance(app.screen, RemoteScreen)


@pytest.mark.asyncio
async def test_force_setup_overrides_existing_config():
    app = LGRemoteApp(config=Config(tv_ip="192.168.1.50"), force_setup=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)
        assert app.screen.initial is True


def test_tv_client_is_none_without_config():
    app = LGRemoteApp(config=None)
    assert app.tv_client is None


def test_tv_client_is_built_from_config():
    app = LGRemoteApp(config=Config(tv_ip="192.168.1.50", client_name="my-client"))
    assert app.tv_client is not None
    assert app.tv_client.ip == "192.168.1.50"
    assert app.tv_client.client_name == "my-client"
