"""Base entity for the HomeOn integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .api import HomeOnAPI
from .const import DOMAIN


class HomeOnEntity(Entity):
    """Common HomeOn entity behavior."""

    _attr_should_poll = False

    def __init__(self, api: HomeOnAPI, device: int | None = None) -> None:
        self._api = api
        self._device = device
        self._attr_available = api.connected
        self._remove_availability_callback = None

    @property
    def device_info(self) -> DeviceInfo | None:
        if self._device is None:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._api.host}:{self._api.port}:{self._device}")},
            name=f"HomeOn controller {self._device}",
            manufacturer="HomeOn",
            model="Automation Controller",
            configuration_url=f"http://{self._api.host}",
        )

    async def async_added_to_hass(self) -> None:
        self._remove_availability_callback = self._api.register_availability_cb(
            self._connection_changed
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_availability_callback is not None:
            self._remove_availability_callback()
            self._remove_availability_callback = None

    def _connection_changed(self, connected: bool) -> None:
        self._attr_available = connected
        self.async_write_ha_state()

    def _write_state(self) -> None:
        if self.hass is not None:
            self.async_write_ha_state()
