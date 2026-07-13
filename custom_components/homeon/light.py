"""Light platform for HomeOn outputs."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
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
    """Set up HomeOn lights."""
    api = config_entry.runtime_data

    @callback
    def add_lights(device: int, config: dict[str, Any], **kwargs: Any) -> None:
        device_type = config.get("type")
        if device_type not in (
            DeviceType.RELAY,
            DeviceType.RELAY_V2,
            DeviceType.MIX,
        ):
            return

        port_count = int(config.get("output_cnt", config.get("relay_cnt", 6)))
        start_port = 0
        if device_type == DeviceType.MIX:
            start_port = int(config.get("blind_cnt", 0)) * 2

        entities: list[HomeOnLight] = []
        for port in range(start_port, port_count):
            entity = HomeOnLight(api, device, port)
            if entity.unique_id in api.entities:
                continue
            api.entities.add(entity.unique_id)
            api.register_cb(
                entity._is_output,
                match={"device": device, "method": "is_output", "port": port},
            )
            entities.append(entity)

        if entities:
            async_add_entities(entities)

    api.register_cb(add_lights, match={"method": "is_config"})


class HomeOnLight(HomeOnEntity, LightEntity):
    """Representation of one HomeOn relay output."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(self, api: Any, device: int, port: int) -> None:
        super().__init__(api, device)
        self._port = port
        self._attr_unique_id = f"homeon_{api.host}_{device}_light_{port}"
        self._default_name = f"Output {port + 1}"
        self._attr_is_on: bool | None = None

    @property
    def name(self) -> str:
        return self._api.db.get_light_alias(
            self._device, self._port, self._default_name
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._api.call(
            method="set_output",
            device=self._device,
            port=self._port,
            value=OutputValue.ON,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._api.call(
            method="set_output",
            device=self._device,
            port=self._port,
            value=OutputValue.OFF,
        )

    @callback
    def _is_output(self, value: int, **kwargs: Any) -> None:
        self._attr_is_on = value == OutputValue.ON
        self._write_state()
