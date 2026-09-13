"""Tests for EEM Online diagnostics."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eem_online.const import UPDATE_INTERVAL
from custom_components.eem_online.data import EemOnlineData
from custom_components.eem_online.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant


async def test_diagnostics_without_coordinator_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Diagnostics remain available before the first successful refresh."""
    coordinator = MagicMock(data=None, last_update_success=False, update_interval=UPDATE_INTERVAL)
    config_entry.runtime_data = EemOnlineData(client=MagicMock(), coordinator=coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["coordinator"] == {
        "last_update_success": False,
        "update_interval": "12:00:00",
        "latest_day": None,
        "latest_consumption": None,
        "latest_meter_day": None,
        "latest_meter_reading": None,
        "summary_available": None,
        "meter_readings_available": None,
    }
