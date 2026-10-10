"""Real Home Assistant objects; transport is isolated from the user's network."""

from types import MappingProxyType
from unittest.mock import Mock

import pytest
import pytest_asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.olimpia_vertigo.const import DOMAIN


@pytest.fixture
def entry():
    return ConfigEntry(
        domain=DOMAIN,
        title="Test Vertigo",
        unique_id="test-device",
        version=1,
        minor_version=1,
        source="user",
        data={"device_id": "test-device", "host": "192.0.2.10", "local_key": "0123456789abcdef"},
        options={},
        discovery_keys=MappingProxyType({}),
        subentries_data=[],
    )


@pytest.fixture
def status():
    return {
        "1": False,
        "2": "1",
        "3": "close",
        "8": False,
        "9": 24,
        "10": 23,
        "11": "0",
        "12": 0,
        "13": 0,
        "102": False,
        "103": False,
        "106": "1",
        "107": True,
    }


@pytest_asyncio.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    yield instance
    await instance.async_stop(force=True)


@pytest.fixture
def transport(monkeypatch, status):
    client = Mock()
    client.status.return_value = {"dps": dict(status)}
    client.set_multiple_values.return_value = {}
    monkeypatch.setattr("custom_components.olimpia_vertigo.api.tinytuya.Device", Mock(return_value=client))
    return client
