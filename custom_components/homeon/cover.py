"""Cover platform for HomeOn blinds."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeOnConfigEntry
from .const import DeviceType, OutputValue
from .entity import HomeOnEntity


async def async_setup_entry(
    hass: Any,
    config_entry: HomeOnConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeOn covers."""
    api = config_entry.runtime_data

    @callback
    def add_covers(device: int, config: dict[str, Any], **kwargs: Any) -> None:
        device_type = config.get("type")
        if device_type == DeviceType.BLIND:
            cover_count = int(config.get("blind_cnt", 3))
        elif device_type == DeviceType.BLIND_V2:
            cover_count = int(config.get("blind_cnt", 4))
        elif device_type == DeviceType.MIX:
            cover_count = int(config.get("blind_cnt", 0))
        else:
            return

        entities: list[HomeOnCover] = []
        for port in range(cover_count):
            entity = HomeOnCover(api, device, port)
            if entity.unique_id in api.entities:
                continue
            api.entities.add(entity.unique_id)
            api.register_cb(
                entity._is_output,
                match={"device": device, "method": "is_output", "port": port},
            )
            api.register_cb(
                entity._is_percent,
                match={"device": device, "method": "is_percent", "port": port},
            )
            entities.append(entity)

        if entities:
            async_add_entities(entities)

    api.register_cb(add_covers, match={"method": "is_config"})


class HomeOnCover(HomeOnEntity, CoverEntity):
    """Representation of one HomeOn blind."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, api: Any, device: int, port: int) -> None:
        super().__init__(api, device)
        self._port = port
        self._attr_unique_id = f"homeon_{api.host}_{device}_cover_{port}"
        self._default_name = f"Blind {port + 1}"
        self._attr_current_cover_position: int | None = None
        self._attr_is_opening = False
        self._attr_is_closing = False

    @property
    def name(self) -> str:
        return self._api.db.get_cover_alias(
            self._device, self._port, self._default_name
        )

    @property
    def is_closed(self) -> bool | None:
        if self._attr_current_cover_position is None:
            return None
        return self._attr_current_cover_position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._api.call(
            method="set_output",
            device=self._device,
            port=self._port,
            value=OutputValue.UP,
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._api.call(
            method="set_output",
            device=self._device,
            port=self._port,
            value=OutputValue.DOWN,
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._api.call(
            method="set_output",
            device=self._device,
            port=self._port,
            value=OutputValue.STOP,
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = int(kwargs[ATTR_POSITION])
        await self._api.call(
            method="set_percent",
            device=self._device,
            port=self._port,
            value=100 - position,
        )

    @callback
    def _is_output(self, value: int, **kwargs: Any) -> None:
        self._attr_is_opening = value == OutputValue.UP
        self._attr_is_closing = value == OutputValue.DOWN
        if value == OutputValue.STOP:
            self._attr_is_opening = False
            self._attr_is_closing = False
        self._write_state()

    @callback
    def _is_percent(self, value: int | float, **kwargs: Any) -> None:
        controller_position = max(0, min(100, int(round(value))))
        self._attr_current_cover_position = 100 - controller_position
        self._write_state()
