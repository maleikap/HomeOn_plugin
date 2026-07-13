"""WebSocket client used by the HomeOn integration."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable
import contextlib
import json
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback

from .const import DEFAULT_CONNECT_TIMEOUT, DEFAULT_RECONNECT_DELAY

_LOGGER = logging.getLogger(__name__)

type MessageCallback = Callable[..., None]
type AvailabilityCallback = Callable[[bool], None]


class MatchAll:
    """Marker matching any protocol value."""


MATCH_ALL = MatchAll()


class HomeOnConnectionError(Exception):
    """Raised when the HomeOn WebSocket cannot be reached."""


class HomeOnDB:
    """Store aliases received from the HomeOn controller."""

    def __init__(self, api: HomeOnAPI) -> None:
        self.api = api
        self.aliases: dict[Any, Any] = defaultdict(dict)
        self.api.register_cb(self._is_aliases, match={"method": "is_aliases"})

    @callback
    def _is_aliases(
        self,
        value: dict[str, Any] | None = None,
        error: Any = None,
        **kwargs: Any,
    ) -> None:
        if error:
            _LOGGER.error("Controller returned an alias database error: %s", error)
            return
        if not isinstance(value, dict):
            _LOGGER.debug("Alias response did not contain a dictionary")
            return

        for raw_addr, data in value.items():
            try:
                addr = int(raw_addr)
            except (TypeError, ValueError):
                continue
            if not isinstance(data, dict):
                continue

            for raw_port, alias in data.get("outputs", {}).items():
                self.aliases[(addr, int(raw_port))] = alias
            for raw_port, alias in data.get("inputs", {}).items():
                self.aliases[(addr, "input", int(raw_port))] = alias
            for raw_port, alias in data.get("counters", {}).items():
                self.aliases[(addr, "counter", int(raw_port))] = alias
            for raw_id, alias in data.get("temperature_sensors", {}).items():
                self.aliases[int(raw_id)] = alias

        _LOGGER.debug("Updated HomeOn aliases: %s", self.aliases)

    def get_light_alias(self, device: int, port: int, default: str) -> str:
        return self.aliases.get((device, port), default)

    def get_cover_alias(self, device: int, port: int, default: str) -> str:
        return self.aliases.get((device, port), default)

    def get_temperature_alias(self, sensor_id: int, default: str) -> str:
        return self.aliases.get(sensor_id, default)

    def get_counter_alias(self, device: int, port: int, default: str) -> str:
        return self.aliases.get((device, "counter", port), default)


class HomeOnAPI:
    """Maintain a resilient local WebSocket connection to HomeOn."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self.hass = hass
        self.host = host
        self.port = port
        self.ws_url = f"ws://{host}:{port}"
        self.ws: Any | None = None
        self.callbacks: list[tuple[dict[str, Any], MessageCallback]] = []
        self.availability_callbacks: set[AvailabilityCallback] = set()
        self.entities: set[str] = set()
        self.connected = False
        self._stopped = False
        self._runner_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self.db = HomeOnDB(self)

    async def async_test_connection(self) -> None:
        """Open and close a connection to validate host and port."""
        try:
            async with asyncio.timeout(DEFAULT_CONNECT_TIMEOUT):
                websocket = await self._open_websocket()
                await websocket.close()
        except Exception as err:
            raise HomeOnConnectionError from err

    async def async_start(self) -> None:
        """Start the persistent connection task."""
        if self._runner_task is not None and not self._runner_task.done():
            return
        self._stopped = False
        self._runner_task = self.hass.async_create_task(
            self._connection_loop(), "HomeOn WebSocket connection"
        )

    async def async_stop(self) -> None:
        """Stop reconnecting and close the socket."""
        self._stopped = True
        task = self._runner_task
        self._runner_task = None

        websocket = self.ws
        self.ws = None
        if websocket is not None:
            with contextlib.suppress(Exception):
                await websocket.close()

        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        self._set_connected(False)

    async def _open_websocket(self) -> Any:
        """Create a WebSocket while supporting bundled websockets versions."""
        import websockets

        return await websockets.connect(
            self.ws_url,
            open_timeout=DEFAULT_CONNECT_TIMEOUT,
            close_timeout=2,
            ping_interval=20,
            ping_timeout=20,
        )

    async def _connection_loop(self) -> None:
        """Connect, read messages, and retry after disconnection."""
        while not self._stopped:
            try:
                _LOGGER.debug("Connecting to %s", self.ws_url)
                self.ws = await self._open_websocket()
                self._set_connected(True)
                _LOGGER.info("Connected to HomeOn at %s", self.ws_url)
                await self.async_initialize()

                async for raw_message in self.ws:
                    await self._handle_message(raw_message)

            except asyncio.CancelledError:
                raise
            except Exception as err:
                if not self._stopped:
                    _LOGGER.warning(
                        "HomeOn connection to %s lost: %s; retrying in %.0f seconds",
                        self.ws_url,
                        err,
                        DEFAULT_RECONNECT_DELAY,
                    )
            finally:
                websocket = self.ws
                self.ws = None
                self._set_connected(False)
                if websocket is not None:
                    with contextlib.suppress(Exception):
                        await websocket.close()

            if not self._stopped:
                await asyncio.sleep(DEFAULT_RECONNECT_DELAY)

    async def _handle_message(self, raw_message: str | bytes) -> None:
        """Decode a protocol message and dispatch it to matching callbacks."""
        try:
            message = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            _LOGGER.warning("Ignoring invalid JSON from HomeOn: %r", raw_message)
            return

        if not isinstance(message, dict):
            _LOGGER.debug("Ignoring non-object HomeOn message: %r", message)
            return

        for match, message_callback in tuple(self.callbacks):
            if self._is_subset(match, message):
                try:
                    message_callback(**message)
                except Exception:
                    _LOGGER.exception("HomeOn message callback failed for %s", message)

    @classmethod
    def _is_subset(cls, expected: dict[str, Any], actual: dict[str, Any]) -> bool:
        for key, expected_value in expected.items():
            if key not in actual:
                return False
            if expected_value is MATCH_ALL:
                continue
            actual_value = actual[key]
            if isinstance(expected_value, dict):
                if not isinstance(actual_value, dict) or not cls._is_subset(
                    expected_value, actual_value
                ):
                    return False
            elif actual_value != expected_value:
                return False
        return True

    async def call(self, **kwargs: Any) -> None:
        """Send a JSON command to the controller."""
        websocket = self.ws
        if websocket is None or not self.connected:
            raise HomeOnConnectionError("HomeOn controller is not connected")

        payload = json.dumps(kwargs, separators=(",", ":"))
        async with self._send_lock:
            try:
                await websocket.send(payload)
            except Exception as err:
                _LOGGER.error("Unable to send HomeOn command %s: %s", kwargs, err)
                raise HomeOnConnectionError from err

    def async_call(self, **kwargs: Any) -> None:
        """Schedule a protocol command without blocking the caller."""
        self.hass.async_create_task(self.call(**kwargs))

    @callback
    def register_cb(
        self, message_callback: MessageCallback, match: dict[str, Any] | None = None
    ) -> Callable[[], None]:
        """Register a callback and return an unsubscribe function."""
        callback_match = match or {}
        item = (callback_match, message_callback)
        self.callbacks.append(item)

        @callback
        def remove_callback() -> None:
            with contextlib.suppress(ValueError):
                self.callbacks.remove(item)

        return remove_callback

    @callback
    def register_availability_cb(
        self, availability_callback: AvailabilityCallback
    ) -> Callable[[], None]:
        """Register for connection-state changes."""
        self.availability_callbacks.add(availability_callback)

        @callback
        def remove_callback() -> None:
            self.availability_callbacks.discard(availability_callback)

        return remove_callback

    @callback
    def _set_connected(self, connected: bool) -> None:
        if self.connected == connected:
            return
        self.connected = connected
        for availability_callback in tuple(self.availability_callbacks):
            availability_callback(connected)

    async def async_initialize(self) -> None:
        """Request aliases, configuration, and initial states."""
        # Older controllers may not implement get_aliases, so it is intentionally
        # sent separately and does not block the configuration request.
        with contextlib.suppress(HomeOnConnectionError):
            await self.call(method="get_aliases")
        await self.call(method="get_config", device=1)
