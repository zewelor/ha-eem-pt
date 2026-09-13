"""Diagnostics for EEM Online."""

from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_CONTRACT

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import EemOnlineConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, CONF_CONTRACT}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: EemOnlineConfigEntry,
) -> dict[str, Any]:
    """Return redacted configuration and normalized coordinator data."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    return {
        "entry": {
            "version": entry.version,
            "state": str(entry.state),
            "data": async_redact_data(entry.data, TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "latest_day": str(data.latest_day) if data and data.latest_day else None,
            "latest_consumption": data.latest_consumption if data else None,
            "latest_meter_day": str(data.latest_meter_day) if data and data.latest_meter_day else None,
            "latest_meter_reading": data.latest_meter_reading if data else None,
            "summary_available": data.summary_available if data else None,
            "meter_readings_available": data.meter_readings_available if data else None,
        },
    }
