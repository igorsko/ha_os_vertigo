"""Blocking local Tuya transport; the coordinator serializes all access."""

import math

import tinytuya

from .const import (
    BEEP,
    HEAT,
    HEAT_LEVEL,
    MODE,
    MODES,
    OSCILLATION,
    POWER,
    SPEED,
    TARGET,
    TIMER,
    UV,
)


class VertigoError(Exception):
    """A local communication failure without credentials in its message."""


def validate_credentials(device_id, host, key):
    """Reject malformed inputs before creating a connection."""
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id")
    if not isinstance(host, str) or not host.strip():
        raise ValueError("host")
    try:
        valid = isinstance(key, str) and len(key.encode("latin1")) == 16
    except UnicodeEncodeError:
        valid = False
    if not valid:
        raise ValueError("local_key")


def validate_command(values):
    """Keep wire types and ranges faithful to the observed device schema."""
    enums = {
        SPEED: set(map(str, range(1, 10))),
        MODE: set(MODES.values()),
        TIMER: set(map(str, range(9))),
        HEAT_LEVEL: set(map(str, range(1, 5))),
    }
    for dp, value in values.items():
        if dp in (POWER, OSCILLATION, BEEP, HEAT, UV):
            valid = type(value) is bool
        elif dp == TARGET:
            valid = type(value) is int and 1 <= value <= 30
        elif dp in enums:
            valid = isinstance(value, str) and value in enums[dp]
        else:
            valid = False
        if not valid:
            raise ValueError("Unsupported parameter or value")


def temperature_command(value):
    """The device rejects float payloads; accept only whole-degree targets."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Temperature must be a whole degree between 1 and 30")
    if not math.isfinite(value) or value != round(value) or not 1 <= value <= 30:
        raise ValueError("Temperature must be a whole degree between 1 and 30")
    return {TARGET: int(value)}


class VertigoAPI:
    """No cloud dependency and no automatic replay of heater commands."""

    def __init__(self, device_id, host, key):
        validate_credentials(device_id, host, key)
        self.device = tinytuya.Device(
            device_id,
            host,
            key,
            version=3.3,
            persist=True,
            connection_timeout=4,
            connection_retry_limit=1,
            connection_retry_delay=1,
        )

    def status(self):
        """Return a valid status frame, never an optimistic state."""
        try:
            result = self.device.status()
            if not isinstance(result, dict) or "Error" in result:
                raise VertigoError("Cannot read local device status")
            values = result.get("dps")
            if not isinstance(values, dict) or not values:
                raise VertigoError("Device did not return parameters")
            return {str(dp): value for dp, value in values.items()}
        except Exception as err:
            self.close()
            raise VertigoError("Cannot read local device status") from err

    def command(self, values):
        """Write once and read back; never retry a potentially applied command."""
        validate_command(values)
        try:
            result = self.device.set_multiple_values(values)
            if isinstance(result, dict) and "Error" in result:
                raise VertigoError("Local command failed")
            return self.status()
        except Exception as err:
            self.close()
            raise VertigoError("Local command failed; check the device state") from err

    def close(self):
        """Release the socket; safe after a communication failure."""
        self.device.close()
