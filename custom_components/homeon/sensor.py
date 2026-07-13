"""Sensor platform for HomeOn."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeOnConfigEntry
from .entity import HomeOnEntity


async def async_setup_entry(
    hass: Any,
    config_entry: HomeOnConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomeOn sensors."""
    api = config_entry.runtime_data

    @callback
    def add_temperature(
        device: int, id: int, value: int | float, **kwargs: Any
    ) -> None:
        entity = HomeOnTemperature(api, device, id)
        if entity.unique_id in api.entities:
            return
        api.entities.add(entity.unique_id)
        api.register_cb(
            entity._is_temperature,
            match={"device": device, "method": "is_temperature", "id": id},
        )
        entity._is_temperature(value)
        async_add_entities([entity])

    @callback
    def add_counter(device: int, id: int, value: Any, **kwargs: Any) -> None:
        entity = HomeOnCounter(api, device, id)
        if entity.unique_id in api.entities:
            return
        api.entities.add(entity.unique_id)
        api.register_cb(
            entity._is_counter,
            match={"device": device, "method": "is_counter", "id": id},
        )
        entity._is_counter(value)
        async_add_entities([entity])

    api.register_cb(add_temperature, match={"method": "is_temperature"})
    api.register_cb(add_counter, match={"method": "is_counter"})


class HomeOnTemperature(HomeOnEntity, SensorEntity):
    """Representation of a HomeOn temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, api: Any, device: int, sensor_id: int) -> None:
        super().__init__(api, device)
        self._sensor_id = sensor_id
        self._attr_unique_id = f"homeon_{api.host}_{device}_temperature_{sensor_id}"
        self._default_name = f"Temperature {sensor_id}"
        self._attr_native_value: float | None = None

    @property
    def name(self) -> str:
        return self._api.db.get_temperature_alias(
            self._sensor_id, self._default_name
        )

    @callback
    def _is_temperature(self, value: int | float, **kwargs: Any) -> None:
        try:
            self._attr_native_value = round(float(value), 1)
        except (TypeError, ValueError):
            self._attr_native_value = None
        self._write_state()


class HomeOnCounter(HomeOnEntity, SensorEntity):
    """Representation of a HomeOn counter."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, api: Any, device: int, counter_id: int) -> None:
        super().__init__(api, device)
        self._counter_id = counter_id
        self._attr_unique_id = f"homeon_{api.host}_{device}_counter_{counter_id}"
        self._default_name = f"Counter {counter_id + 1}"
        self._attr_native_value: int | float | None = None

    @property
    def name(self) -> str:
        return self._api.db.get_counter_alias(
            self._device, self._counter_id, self._default_name
        )

    @callback
    def _is_counter(self, value: Any, **kwargs: Any) -> None:
        self._attr_native_value = value if isinstance(value, (int, float)) else None
        self._write_state()
