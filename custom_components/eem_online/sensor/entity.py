"""Sensor backed by EEM coordinator data."""

from custom_components.eem_online.entity import EemOnlineEntity
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.typing import StateType


class EemOnlineSensor(SensorEntity, EemOnlineEntity):
    """Expose one value from the coordinator payload."""

    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """Return the current value."""
        if self.entity_description.key == "meter_reading":
            return self.coordinator.data.latest_meter_reading
        return self.coordinator.data.latest_consumption

    @property
    def available(self) -> bool:
        """Return whether this sensor's source is available."""
        if not super().available:
            return False
        if self.entity_description.key == "meter_reading":
            return self.coordinator.data.meter_readings_available
        return self.coordinator.data.summary_available

    @property
    def extra_state_attributes(self) -> dict[str, StateType]:
        """Return the operator day represented by the value."""
        if self.entity_description.key == "meter_reading":
            latest_day = self.coordinator.data.latest_meter_day
            return {"reading_date": latest_day.isoformat() if latest_day else None}
        latest_day = self.coordinator.data.latest_day
        return {"consumption_date": latest_day.isoformat() if latest_day else None}
