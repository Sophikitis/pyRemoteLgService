import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from bscpylgtv.exceptions import PyLGTVCmdException, PyLGTVPairException

from lg_remote.tv_client import (
    DEFAULT_KEY_FILE_PATH,
    TVClient,
    TVConnectionError,
    TVPairingRejectedError,
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


@pytest.mark.asyncio
async def test_connect_passes_key_file_path_next_to_config():
    fake_client = AsyncMock()
    with _patched_create(fake_client) as create_mock:
        tv = TVClient("192.168.1.10")
        await tv.connect()

    assert create_mock.await_args.kwargs["key_file_path"] == str(DEFAULT_KEY_FILE_PATH)


@pytest.mark.asyncio
async def test_pairing_rejected_raises_tv_pairing_rejected_and_stays_disconnected():
    fake_client = AsyncMock()
    fake_client.connect.side_effect = PyLGTVPairException("Unable to pair")
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        with pytest.raises(TVPairingRejectedError):
            await tv.connect()

    assert tv.is_connected is False
    assert issubclass(TVPairingRejectedError, TVConnectionError)


@pytest.mark.asyncio
async def test_pairing_rejected_during_pairing_wait_raises_tv_pairing_rejected():
    fake_client = AsyncMock()
    fake_client.connect.side_effect = PyLGTVPairException("Unable to pair")
    with _patched_create(fake_client):
        tv = TVClient("192.168.1.10")
        with pytest.raises(TVPairingRejectedError):
            await tv.connect_with_pairing()

    assert tv.is_connected is False


@pytest.mark.asyncio
async def test_command_failure_wraps_exception_and_invalidates_client():
    tv, fake_client = _connected_client()
    fake_client.button.side_effect = PyLGTVCmdException("Not connected")

    with pytest.raises(TVConnectionError):
        await tv.home()

    assert tv.is_connected is False


def test_command_log_starts_empty():
    tv = TVClient("192.168.1.10")
    assert tv.command_log == []


def test_all_exceptions_are_tv_connection_errors():
    assert issubclass(TVUnreachableError, TVConnectionError)
    assert issubclass(TVTimeoutError, TVConnectionError)
    assert issubclass(TVPairingTimeoutError, TVConnectionError)


def _connected_client():
    tv = TVClient("192.168.1.10")
    fake_client = AsyncMock()
    tv._client = fake_client
    return tv, fake_client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "button_name"),
    [
        ("home", "HOME"),
        ("back", "BACK"),
        ("exit", "EXIT"),
        ("nav_up", "UP"),
        ("nav_down", "DOWN"),
        ("nav_left", "LEFT"),
        ("nav_right", "RIGHT"),
        ("ok", "ENTER"),
        ("mute", "MUTE"),
        ("info", "INFO"),
        ("input_source", "INPUT_HUB"),
    ],
)
async def test_button_based_actions_send_the_right_button(method_name, button_name):
    tv, fake_client = _connected_client()

    await getattr(tv, method_name)()

    fake_client.button.assert_awaited_once_with(button_name)
    assert tv.command_log[-1] == f"button {button_name}"


@pytest.mark.asyncio
async def test_power_calls_power_off():
    tv, fake_client = _connected_client()
    await tv.power()
    fake_client.power_off.assert_awaited_once()
    assert tv.command_log[-1] == "power_off"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "bscpylgtv_method"),
    [
        ("volume_up", "volume_up"),
        ("volume_down", "volume_down"),
        ("channel_up", "channel_up"),
        ("channel_down", "channel_down"),
    ],
)
async def test_dedicated_methods_are_forwarded(method_name, bscpylgtv_method):
    tv, fake_client = _connected_client()
    await getattr(tv, method_name)()
    getattr(fake_client, bscpylgtv_method).assert_awaited_once()


@pytest.mark.asyncio
async def test_netflix_launches_the_netflix_app():
    tv, fake_client = _connected_client()
    await tv.netflix()
    fake_client.launch_app.assert_awaited_once_with("netflix")


@pytest.mark.asyncio
async def test_open_in_start_uses_factorywin_with_instart_irkey():
    tv, fake_client = _connected_client()
    await tv.open_in_start()
    fake_client.launch_app_with_params.assert_awaited_once_with(
        "com.webos.app.factorywin", {"id": "executeFactory", "irKey": "inStart"}
    )


@pytest.mark.asyncio
async def test_open_ez_adjust_uses_factorywin_with_ezadjust_irkey():
    tv, fake_client = _connected_client()
    await tv.open_ez_adjust()
    fake_client.launch_app_with_params.assert_awaited_once_with(
        "com.webos.app.factorywin", {"id": "executeFactory", "irKey": "ezAdjust"}
    )


@pytest.mark.asyncio
async def test_action_without_connection_raises_tv_connection_error():
    tv = TVClient("192.168.1.10")
    with pytest.raises(TVConnectionError):
        await tv.home()


@pytest.mark.asyncio
async def test_command_log_is_capped_at_twenty_entries():
    tv, _fake_client = _connected_client()
    for _ in range(25):
        await tv.home()
    assert len(tv.command_log) == 20
