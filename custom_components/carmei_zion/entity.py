"""Base entity: all entities sit on one device called "CZ"."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import CarmeiZionCoordinator


class CarmeiZionEntity(CoordinatorEntity[CarmeiZionCoordinator]):
    """Common device + naming. With has_entity_name, "CZ" + "Friday Mincha" -> sensor.cz_friday_mincha."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: CarmeiZionCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="CZ",
            manufacturer="Carmei Zion",
            model="Weekly schedule",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.url.rsplit("/", 1)[0] + "/",
        )

    @property
    def available(self) -> bool:
        # Stay available on the saved schedule even if the latest download failed.
        return self.coordinator.data is not None and self.coordinator.data.schedule is not None
