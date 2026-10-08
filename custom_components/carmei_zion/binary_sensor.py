"""'Schedule Up To Date': on while the times are for this week's Shabbat."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import CarmeiZionConfigEntry, CarmeiZionCoordinator
from .entity import CarmeiZionEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarmeiZionConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the binary sensor."""
    async_add_entities([UpToDateSensor(entry.runtime_data)])


class UpToDateSensor(CarmeiZionEntity, BinarySensorEntity):
    """Off when this week's flyer hasn't been published yet, so last week's times are showing."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: CarmeiZionCoordinator) -> None:
        super().__init__(coordinator, "schedule_up_to_date", "Schedule Up To Date")

    @property
    def available(self) -> bool:
        # Always report: "off" is the useful answer when there is no schedule at all.
        return True

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        return bool(data and data.schedule and data.schedule.is_current(dt_util.now()))
