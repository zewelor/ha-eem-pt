"""Tests for setup, entities, and device ownership."""

from dataclasses import replace

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eem_online.const import DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


@pytest.mark.freeze_time("2026-09-13 12:00:00+00:00")
async def test_setup_entities_and_unload(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """One contract exposes two sensors on one service device."""
    assert init_integration.state is ConfigEntryState.LOADED
    consumption = hass.states.get("sensor.eem_online_123456_latest_daily_consumption")
    assert consumption is not None
    assert consumption.state == "3.5"
    assert consumption.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfEnergy.KILO_WATT_HOUR
    assert consumption.attributes["consumption_date"] == "2026-09-12"
    assert hass.states.get("sensor.eem_online_123456_latest_consumption_date") is None

    meter_reading = hass.states.get("sensor.eem_online_123456_meter_reading")
    assert meter_reading is not None
    assert meter_reading.state == "10182.0"
    assert meter_reading.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfEnergy.KILO_WATT_HOUR
    assert meter_reading.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.ENERGY
    assert "state_class" not in meter_reading.attributes
    assert meter_reading.attributes["reading_date"] == "2026-09-12"

    entity_entry = er.async_get(hass).async_get("sensor.eem_online_123456_meter_reading")
    assert entity_entry is not None
    assert entity_entry.unique_id == "123456_meter_reading"
    entities = er.async_entries_for_config_entry(er.async_get(hass), init_integration.entry_id)
    assert {entry.entity_id for entry in entities} == {
        "sensor.eem_online_123456_latest_daily_consumption",
        "sensor.eem_online_123456_meter_reading",
    }

    coordinator = init_integration.runtime_data.coordinator
    coordinator.async_set_updated_data(replace(coordinator.data, meter_readings_available=False))
    await hass.async_block_till_done()
    consumption = hass.states.get("sensor.eem_online_123456_latest_daily_consumption")
    meter_reading = hass.states.get("sensor.eem_online_123456_meter_reading")
    assert consumption is not None
    assert meter_reading is not None
    assert consumption.state == "3.5"
    assert meter_reading.state == "unavailable"

    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, "123456"), init_integration.entry_id)
    assert device is not None
    assert device.manufacturer == "EEM"

    assert await hass.config_entries.async_unload(init_integration.entry_id)
    assert init_integration.state is ConfigEntryState.NOT_LOADED
