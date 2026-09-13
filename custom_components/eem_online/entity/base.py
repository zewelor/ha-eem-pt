"""Base entity for EEM Online."""

from typing import TYPE_CHECKING

from custom_components.eem_online.const import ATTRIBUTION, CONF_CONTRACT, DOMAIN
from custom_components.eem_online.coordinator import EemOnlineDataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class EemOnlineEntity(CoordinatorEntity[EemOnlineDataUpdateCoordinator]):
    """Attach coordinator entities to the configured EEM contract."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: EemOnlineDataUpdateCoordinator, description: EntityDescription) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        contract = coordinator.config_entry.data[CONF_CONTRACT]
        self._attr_unique_id = f"{contract}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, contract)},
            name=f"EEM Online {contract}",
            manufacturer="EEM",
        )
