"""Credential, payload, communication and read-back regressions."""

import pytest

from custom_components.olimpia_vertigo.api import (
    VertigoAPI,
    VertigoError,
    temperature_command,
    validate_command,
    validate_credentials,
)


@pytest.mark.parametrize("key", ["", "short", "x" * 17, "😀" * 16, None])
def test_invalid_keys(key):
    with pytest.raises(ValueError):
        validate_credentials("test-device", "192.0.2.10", key)


@pytest.mark.parametrize("value", [24.5, float("nan"), float("inf"), 0, 31, True, "24"])
def test_reject_invalid_temperature(value):
    with pytest.raises(ValueError):
        temperature_command(value)


def test_temperature_is_integer():
    assert temperature_command(24.0) == {"9": 24}
    assert type(temperature_command(24.0)["9"]) is int


@pytest.mark.parametrize("values", [{"9": 24.0}, {"2": 2}, {"1": 1}, {"10": 20}, {"3": "turbo"}])
def test_reject_wrong_wire_types(values):
    with pytest.raises(ValueError):
        validate_command(values)


@pytest.mark.parametrize("reply", [None, {"Error": "network"}, {}, {"dps": {}}])
def test_bad_status_closes_connection(transport, reply):
    transport.status.return_value = reply
    api = VertigoAPI("test-device", "192.0.2.10", "0123456789abcdef")
    with pytest.raises(VertigoError):
        api.status()
    transport.close.assert_called_once()


def test_readback_does_not_assume_write_succeeded(transport):
    api = VertigoAPI("test-device", "192.0.2.10", "0123456789abcdef")
    result = api.command({"1": True})
    assert result["1"] is False
    transport.set_multiple_values.assert_called_once_with({"1": True})


def test_failed_write_is_not_retried(transport):
    transport.set_multiple_values.return_value = {"Error": "network"}
    api = VertigoAPI("test-device", "192.0.2.10", "0123456789abcdef")
    with pytest.raises(VertigoError):
        api.command({"103": True})
    transport.set_multiple_values.assert_called_once()
    transport.status.assert_not_called()
