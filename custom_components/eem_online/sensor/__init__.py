"""Sensor platform for EEM Online."""

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from homeassistant.const import UnitOfEnergy

from .entity import EemOnlineSensor

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from custom_components.eem_online.data import EemOnlineConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="latest_consumption",
        translation_key="latest_consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="meter_reading",
        translation_key="meter_reading",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EemOnlineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the EEM Online sensors."""
    async_add_entities(
        EemOnlineSensor(entry.runtime_data.coordinator, description) for description in ENTITY_DESCRIPTIONS
    )
