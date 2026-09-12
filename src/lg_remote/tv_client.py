from __future__ import annotations

import asyncio
from pathlib import Path

from bscpylgtv import WebOsClient
from bscpylgtv.exceptions import (
    PyLGTVCmdException,
    PyLGTVPairException,
)

from .config import DEFAULT_CONFIG_PATH

CONNECT_TIMEOUT_SECONDS = 3
PAIRING_TIMEOUT_SECONDS = 60

# bscpylgtv's own default key storage resolves relative to the current
# working directory no matter what (see StorageSqliteDict.__init__ — the
# cwd branch runs unconditionally, HOME is never actually used). Passing
# an explicit path keeps the pairing key stable across launch directories,
# next to the rest of our own config.
DEFAULT_KEY_FILE_PATH = DEFAULT_CONFIG_PATH.parent / "client_key.sqlite"

# bscpylgtv exceptions that mean "the command/connection attempt failed on
# the TV side" rather than "our code is broken" — always translated into
# our own TVConnectionError family so callers only ever need to catch one
# hierarchy, regardless of which bscpylgtv internals raised.
_TV_SIDE_ERRORS = (PyLGTVPairException, PyLGTVCmdException, ConnectionError, OSError)


class TVConnectionError(Exception):
    """Base class for all TV connection failures."""


class TVUnreachableError(TVConnectionError):
    """The TV refused the connection or the host is unreachable."""


class TVTimeoutError(TVConnectionError):
    """The TV did not finish connecting within the normal timeout."""


class TVPairingTimeoutError(TVConnectionError):
    """The on-screen pairing prompt was not accepted in time."""


class TVPairingRejectedError(TVConnectionError):
    """The pairing request was explicitly refused or failed on the TV."""


class TVClient:
    """Thin async wrapper around bscpylgtv.WebOsClient.

    Screens only ever talk to this class, never to bscpylgtv directly.
    """

    def __init__(
        self,
        ip: str,
        client_name: str = "lg-remote-tui",
        key_file_path: Path | None = DEFAULT_KEY_FILE_PATH,
    ) -> None:
        self.ip = ip
        self.client_name = client_name
        self.key_file_path = key_file_path
        self._client: WebOsClient | None = None
        self.command_log: list[str] = []

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def _create_client_kwargs(self, timeout_connect: int) -> dict:
        if self.key_file_path is not None:
            self.key_file_path.parent.mkdir(parents=True, exist_ok=True)
        return dict(
            client_key=None,
            key_file_path=(
                str(self.key_file_path) if self.key_file_path is not None else None
            ),
            timeout_connect=timeout_connect,
            connect_retry_attempts=1,
            get_hello_info=False,
        )

    async def connect(self, timeout_connect: float = CONNECT_TIMEOUT_SECONDS) -> None:
        """Fast connection attempt for an already-paired TV.

        Raises TVUnreachableError quickly if the host refuses the
        connection, or TVTimeoutError if it doesn't finish connecting in
        time (this also covers the case where the TV is waiting for an
        on-screen pairing approval that hasn't happened yet — the caller
        should fall back to connect_with_pairing() in that case).
        """
        client = await WebOsClient.create(
            self.ip, **self._create_client_kwargs(int(timeout_connect) or 1)
        )
        try:
            await asyncio.wait_for(client.connect(), timeout=timeout_connect)
        except asyncio.TimeoutError as exc:
            await client.disconnect()
            raise TVTimeoutError(
                f"TV at {self.ip} did not respond within {timeout_connect}s"
            ) from exc
        except PyLGTVPairException as exc:
            await self._silent_disconnect(client)
            raise TVPairingRejectedError(
                f"Pairing with the TV at {self.ip} failed: {exc}"
            ) from exc
        except (ConnectionRefusedError, OSError) as exc:
            raise TVUnreachableError(f"TV at {self.ip} is unreachable: {exc}") from exc
        self._client = client

    async def connect_with_pairing(
        self, pairing_timeout: float = PAIRING_TIMEOUT_SECONDS
    ) -> None:
        """Connection attempt that waits for the on-screen pairing prompt."""
        client = await WebOsClient.create(
            self.ip, **self._create_client_kwargs(int(CONNECT_TIMEOUT_SECONDS))
        )
        try:
            await asyncio.wait_for(client.connect(), timeout=pairing_timeout)
        except asyncio.TimeoutError as exc:
            await client.disconnect()
            raise TVPairingTimeoutError(
                f"Pairing prompt on the TV at {self.ip} was not accepted "
                f"within {pairing_timeout}s"
            ) from exc
        except PyLGTVPairException as exc:
            await self._silent_disconnect(client)
            raise TVPairingRejectedError(
                f"Pairing with the TV at {self.ip} failed: {exc}"
            ) from exc
        except (ConnectionRefusedError, OSError) as exc:
            raise TVUnreachableError(f"TV at {self.ip} is unreachable: {exc}") from exc
        self._client = client

    @staticmethod
    async def _silent_disconnect(client: WebOsClient) -> None:
        try:
            await client.disconnect()
        except Exception:
            # Best-effort cleanup of a connection attempt that already
            # failed — its own disconnect failing is not a new error.
            pass

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

    async def _run_command(self, awaitable, description: str) -> None:
        """Await a single bscpylgtv call, translating its failures.

        Any TV-side failure (a rejected command, the connection dropping
        mid-command, ...) becomes a TVConnectionError and invalidates
        this client's connected state, so is_connected reflects reality
        instead of a connect() that merely succeeded once in the past.
        """
        try:
            await awaitable
        except _TV_SIDE_ERRORS as exc:
            self._client = None
            raise TVConnectionError(f"TV command failed: {exc}") from exc
        self._log(description)

    async def _button(self, name: str) -> None:
        self._require_connected()
        await self._run_command(self._client.button(name), f"button {name}")

    async def power(self) -> None:
        self._require_connected()
        await self._run_command(self._client.power_off(), "power_off")

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
        await self._run_command(self._client.volume_up(), "volume_up")

    async def volume_down(self) -> None:
        self._require_connected()
        await self._run_command(self._client.volume_down(), "volume_down")

    async def channel_up(self) -> None:
        self._require_connected()
        await self._run_command(self._client.channel_up(), "channel_up")

    async def channel_down(self) -> None:
        self._require_connected()
        await self._run_command(self._client.channel_down(), "channel_down")

    async def netflix(self) -> None:
        self._require_connected()
        await self._run_command(
            self._client.launch_app("netflix"), "launch_app netflix"
        )

    async def open_in_start(self) -> None:
        self._require_connected()
        await self._run_command(
            self._client.launch_app_with_params(
                "com.webos.app.factorywin",
                {"id": "executeFactory", "irKey": "inStart"},
            ),
            "launch_app_with_params factorywin inStart",
        )

    async def open_ez_adjust(self) -> None:
        self._require_connected()
        await self._run_command(
            self._client.launch_app_with_params(
                "com.webos.app.factorywin",
                {"id": "executeFactory", "irKey": "ezAdjust"},
            ),
            "launch_app_with_params factorywin ezAdjust",
        )
