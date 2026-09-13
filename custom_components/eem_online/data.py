"""Runtime data types for EEM Online."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .api import EemOnlineApiClient
    from .coordinator import EemOnlineDataUpdateCoordinator


@dataclass(frozen=True, slots=True)
class EemOnlineDailyConsumption:
    """Consumption reported for one operator day."""

    day: date
    start: datetime
    value: float


@dataclass(frozen=True, slots=True)
class EemOnlineCoordinatorData:
    """Small payload shared by all entities."""

    latest_day: date | None
    latest_consumption: float | None
    latest_meter_day: date | None
    latest_meter_reading: float | None
    summary_available: bool
    meter_readings_available: bool


@dataclass(slots=True)
class EemOnlineData:
    """Runtime objects owned by a config entry."""

    client: EemOnlineApiClient
    coordinator: EemOnlineDataUpdateCoordinator


type EemOnlineConfigEntry = ConfigEntry[EemOnlineData]
