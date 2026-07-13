"""Constants for the HomeOn integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "homeon"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"

DEFAULT_HOST: Final = "127.0.0.1"
DEFAULT_PORT: Final = 18080
DEFAULT_CONNECT_TIMEOUT: Final = 5.0
DEFAULT_RECONNECT_DELAY: Final = 5.0


class DeviceType:
    """HomeOn device type values."""

    UNSET = 0x00
    RELAY = 0x01
    RELAIS = RELAY  # Backwards-compatible protocol name.
    BLIND = 0x02
    INPUT20 = 0x03
    DIMMER_24V = 0x04
    RELAY_V2 = 0x05
    RELAIS_V2 = RELAY_V2
    BLIND_V2 = 0x06
    DIMMER_10V = 0x07
    DIMMER_230V = 0x07
    MIX = 0x08


class OutputValue:
    """HomeOn output command values."""

    OFF = 0x00
    ON = 0x01
    UP = 0x02
    DOWN = 0x03
    STOP = 0x04
    TOGGLE = 0x05


class InputValue:
    """HomeOn input event values."""

    SHORT = 0x00
    LONG_DOWN = 0x01
    LONG_UP = 0x02


# Compatibility aliases for older modules using the original names.
device_t = DeviceType
outval_t = OutputValue
inval_t = InputValue
