"""Tests for setup, entities, and device ownership."""

from dataclasses import replace
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.eem_online.const import DOMAIN, UPDATE_INTERVAL
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util


@pytest.mark.freeze_time("2026-09-13 12:00:00+00:00")
async def test_meter_reading_ignores_zero_placeholders_across_updates(
    recorder_mock: object,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_api_client: AsyncMock,
    mock_statistics: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Zero duplicates and newer placeholders cannot overwrite an actual reading."""
    mock_api_client.async_get_meter_readings.return_value = [
        {"data": "2026-09-11T00:00:00", "totalRegistadores": 10182.0},
        {"data": "2026-09-11T12:00:00", "totalRegistadores": 0.0},
        {"data": "2026-09-12T00:00:00", "totalRegistadores": 0.0},
    ]
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "sensor.eem_online_123456_meter_reading"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "10182.0"
    assert state.attributes["reading_date"] == "2026-09-11"

    mock_api_client.async_get_meter_readings.return_value = [
        {"data": "2026-09-12T00:00:00", "totalRegistadores": 0.0},
    ]
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert mock_api_client.async_get_meter_readings.await_count == 2
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "10182.0"
    assert state.attributes["reading_date"] == "2026-09-11"

    mock_api_client.async_get_meter_readings.return_value = [
        {"data": "2026-09-13T00:00:00", "totalRegistadores": 10195.0},
    ]
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert mock_api_client.async_get_meter_readings.await_count == 3
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "10195.0"
    assert state.attributes["reading_date"] == "2026-09-13"


@pytest.mark.freeze_time("2026-09-13 12:00:00+00:00")
async def test_zero_only_meter_readings_at_startup_remain_unknown(
    recorder_mock: object,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_api_client: AsyncMock,
    mock_statistics: AsyncMock,
) -> None:
    """A successful request with only placeholders cannot invent a meter reading."""
    mock_api_client.async_get_meter_readings.return_value = [
        {"data": "2026-09-12T00:00:00", "totalRegistadores": 0.0},
    ]
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.eem_online_123456_meter_reading")
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["reading_date"] is None
    consumption = hass.states.get("sensor.eem_online_123456_latest_daily_consumption")
    assert consumption is not None
    assert consumption.state == "3.5"


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
