from __future__ import annotations

import asyncio

from bscpylgtv import WebOsClient

CONNECT_TIMEOUT_SECONDS = 3
PAIRING_TIMEOUT_SECONDS = 60


class TVConnectionError(Exception):
    """Base class for all TV connection failures."""


class TVUnreachableError(TVConnectionError):
    """The TV refused the connection or the host is unreachable."""


class TVTimeoutError(TVConnectionError):
    """The TV did not finish connecting within the normal timeout."""


class TVPairingTimeoutError(TVConnectionError):
    """The on-screen pairing prompt was not accepted in time."""


class TVClient:
    """Thin async wrapper around bscpylgtv.WebOsClient.

    Screens only ever talk to this class, never to bscpylgtv directly.
    """

    def __init__(self, ip: str, client_name: str = "lg-remote-tui") -> None:
        self.ip = ip
        self.client_name = client_name
        self._client: WebOsClient | None = None
        self.command_log: list[str] = []

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def connect(self, timeout_connect: float = CONNECT_TIMEOUT_SECONDS) -> None:
        """Fast connection attempt for an already-paired TV.

        Raises TVUnreachableError quickly if the host refuses the
        connection, or TVTimeoutError if it doesn't finish connecting in
        time (this also covers the case where the TV is waiting for an
        on-screen pairing approval that hasn't happened yet — the caller
        should fall back to connect_with_pairing() in that case).
        """
        client = await WebOsClient.create(
            self.ip,
            client_key=None,
            timeout_connect=int(timeout_connect) or 1,
            connect_retry_attempts=1,
            get_hello_info=False,
        )
        try:
            await asyncio.wait_for(client.connect(), timeout=timeout_connect)
        except asyncio.TimeoutError as exc:
            await client.disconnect()
            raise TVTimeoutError(
                f"TV at {self.ip} did not respond within {timeout_connect}s"
            ) from exc
        except (ConnectionRefusedError, OSError) as exc:
            raise TVUnreachableError(f"TV at {self.ip} is unreachable: {exc}") from exc
        self._client = client

    async def connect_with_pairing(
        self, pairing_timeout: float = PAIRING_TIMEOUT_SECONDS
    ) -> None:
        """Connection attempt that waits for the on-screen pairing prompt."""
        client = await WebOsClient.create(
            self.ip,
            client_key=None,
            timeout_connect=int(CONNECT_TIMEOUT_SECONDS),
            connect_retry_attempts=1,
            get_hello_info=False,
        )
        try:
            await asyncio.wait_for(client.connect(), timeout=pairing_timeout)
        except asyncio.TimeoutError as exc:
            await client.disconnect()
            raise TVPairingTimeoutError(
                f"Pairing prompt on the TV at {self.ip} was not accepted "
                f"within {pairing_timeout}s"
            ) from exc
        except (ConnectionRefusedError, OSError) as exc:
            raise TVUnreachableError(f"TV at {self.ip} is unreachable: {exc}") from exc
        self._client = client

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    def _require_connected(self) -> None:
        if self._client is None:
            raise TVConnectionError("Not connected to the TV")

    def _log(self, description: str) -> None:
        self.command_log.append(description)
        del self.command_log[:-20]

    async def _button(self, name: str) -> None:
        self._require_connected()
        await self._client.button(name)
        self._log(f"button {name}")

    async def power(self) -> None:
        self._require_connected()
        await self._client.power_off()
        self._log("power_off")

    async def home(self) -> None:
        await self._button("HOME")

    async def back(self) -> None:
        await self._button("BACK")

    async def exit(self) -> None:
        await self._button("EXIT")

    async def nav_up(self) -> None:
        await self._button("UP")

    async def nav_down(self) -> None:
        await self._button("DOWN")

    async def nav_left(self) -> None:
        await self._button("LEFT")

    async def nav_right(self) -> None:
        await self._button("RIGHT")

    async def ok(self) -> None:
        await self._button("ENTER")

    async def mute(self) -> None:
        await self._button("MUTE")

    async def info(self) -> None:
        await self._button("INFO")

    async def input_source(self) -> None:
        await self._button("INPUT_HUB")

    async def volume_up(self) -> None:
        self._require_connected()
        await self._client.volume_up()
        self._log("volume_up")

    async def volume_down(self) -> None:
        self._require_connected()
        await self._client.volume_down()
        self._log("volume_down")

    async def channel_up(self) -> None:
        self._require_connected()
        await self._client.channel_up()
        self._log("channel_up")

    async def channel_down(self) -> None:
        self._require_connected()
        await self._client.channel_down()
        self._log("channel_down")

    async def netflix(self) -> None:
        self._require_connected()
        await self._client.launch_app("netflix")
        self._log("launch_app netflix")

    async def open_in_start(self) -> None:
        self._require_connected()
        await self._client.launch_app_with_params(
            "com.webos.app.factorywin", {"id": "executeFactory", "irKey": "inStart"}
        )
        self._log("launch_app_with_params factorywin inStart")

    async def open_ez_adjust(self) -> None:
        self._require_connected()
        await self._client.launch_app_with_params(
            "com.webos.app.factorywin", {"id": "executeFactory", "irKey": "ezAdjust"}
        )
        self._log("launch_app_with_params factorywin ezAdjust")
