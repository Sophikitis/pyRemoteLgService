import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from lg_remote.tv_client import (
    TVClient,
    TVConnectionError,
    TVPairingTimeoutError,
    TVTimeoutError,
    TVUnreachableError,
)


def _patched_create(fake_client):
    return patch(
        "lg_remote.tv_client.WebOsClient.create",
        AsyncMock(return_value=fake_client),
    )


@pytest.mark.asyncio
async def test_connect_success_marks_client_connected():
    fake_client = AsyncMock()
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        await tv.connect()

    assert tv.is_connected is True
    fake_client.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_refused_raises_unreachable_and_stays_disconnected():
    fake_client = AsyncMock()
    fake_client.connect.side_effect = ConnectionRefusedError()
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        with pytest.raises(TVUnreachableError):
            await tv.connect()

    assert tv.is_connected is False


@pytest.mark.asyncio
async def test_connect_that_never_returns_raises_tv_timeout_error():
    fake_client = AsyncMock()

    async def hang_forever(*args, **kwargs):
        await asyncio.sleep(10)

    fake_client.connect.side_effect = hang_forever
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        with pytest.raises(TVTimeoutError):
            await tv.connect(timeout_connect=0.05)

    assert tv.is_connected is False
    fake_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_with_pairing_success_marks_client_connected():
    fake_client = AsyncMock()
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        await tv.connect_with_pairing()

    assert tv.is_connected is True


@pytest.mark.asyncio
async def test_connect_with_pairing_timeout_disconnects_and_raises():
    fake_client = AsyncMock()

    async def hang_forever(*args, **kwargs):
        await asyncio.sleep(10)

    fake_client.connect.side_effect = hang_forever
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        with pytest.raises(TVPairingTimeoutError):
            await tv.connect_with_pairing(pairing_timeout=0.05)

    assert tv.is_connected is False
    fake_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_clears_connected_state():
    fake_client = AsyncMock()
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        await tv.connect()
        await tv.disconnect()

    assert tv.is_connected is False
    fake_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_when_never_connected_is_a_no_op():
    tv = TVClient("192.168.1.10")
    await tv.disconnect()  # must not raise
    assert tv.is_connected is False


def test_command_log_starts_empty():
    tv = TVClient("192.168.1.10")
    assert tv.command_log == []


def test_all_exceptions_are_tv_connection_errors():
    assert issubclass(TVUnreachableError, TVConnectionError)
    assert issubclass(TVTimeoutError, TVConnectionError)
    assert issubclass(TVPairingTimeoutError, TVConnectionError)
