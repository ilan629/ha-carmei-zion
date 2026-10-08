"""Sensors: one timestamp sensor per time on the flyer, plus the parasha."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import SHABBAT_SENSORS, WEEKDAY_SENSORS
from .coordinator import CarmeiZionConfigEntry, CarmeiZionCoordinator
from .entity import CarmeiZionEntity
from .schedule import Schedule


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarmeiZionConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create all sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        TimeSensor(coordinator, "candle_lighting", "Friday Candle Lighting", "mdi:candle", lambda s, _n: s.candle_lighting_at()),
        TimeSensor(coordinator, "tzeit_shabbat", "Tzeit Shabbat", "mdi:star-four-points-outline", lambda s, _n: s.havdala_at()),
    ]
    for key, (name, _day, icon) in SHABBAT_SENSORS.items():
        entities.append(TimeSensor(coordinator, f"shabbat_{key}", name, icon, _shabbat_getter(key)))
    for key, (name, days, icon) in WEEKDAY_SENSORS.items():
        for day in days:
            entities.append(
                TimeSensor(coordinator, f"{day.lower()}_{key}", f"{day} {name}", icon, _weekday_getter(key, day))
            )
    entities += [ParashaSensor(coordinator), LastUpdatedSensor(coordinator)]
    async_add_entities(entities)


def _shabbat_getter(key: str) -> Callable[[Schedule, datetime], datetime | None]:
    return lambda s, _now: s.shabbat_at(key)


def _weekday_getter(key: str, day: str) -> Callable[[Schedule, datetime], datetime | None]:
    return lambda s, now: s.next_weekday_at(key, day, now)


class TimeSensor(CarmeiZionEntity, SensorEntity):
    """A prayer time. State is a full timestamp, so it works as a time trigger (with offsets)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: CarmeiZionCoordinator,
        key: str,
        name: str,
        icon: str,
        getter: Callable[[Schedule, datetime], datetime | None],
    ) -> None:
        super().__init__(coordinator, key, name)
        self._attr_icon = icon
        self._getter = getter

    @property
    def native_value(self) -> datetime | None:
        schedule = self.coordinator.data.schedule
        return self._getter(schedule, dt_util.now()) if schedule else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # "19:05", for dashboards that want the plain time.
        value = self.native_value
        schedule = self.coordinator.data.schedule
        return {"time": value.astimezone(schedule.tz).strftime("%H:%M") if value and schedule else None}


class ParashaSensor(CarmeiZionEntity, SensorEntity):
    """This week's parasha, with the whole schedule as attributes."""

    _attr_icon = "mdi:book-open-page-variant"

    def __init__(self, coordinator: CarmeiZionCoordinator) -> None:
        super().__init__(coordinator, "parasha", "Parasha")

    @property
    def native_value(self) -> str | None:
        schedule = self.coordinator.data.schedule
        return schedule.parasha or None if schedule else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedule = self.coordinator.data.schedule
        if not schedule:
            return {}
        raw = schedule.raw
        return {
            "erev_date": schedule.erev_date.isoformat(),
            "shabbat_date": schedule.shabbat_date.isoformat(),
            "candle_lighting": schedule.candle_lighting,
            "havdala": schedule.havdala,
            "shabbat_times": raw.get("shabbat") or [],
            "weekday_times": raw.get("weekdays") or [],
        }


class LastUpdatedSensor(CarmeiZionEntity, SensorEntity):
    """When the schedule in use was downloaded; the latest problem (if any) as an attribute."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cloud-download-outline"

    def __init__(self, coordinator: CarmeiZionCoordinator) -> None:
        super().__init__(coordinator, "last_updated", "Last Updated")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.fetched_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"last_problem": self.coordinator.data.last_error, "feed_url": self.coordinator.url}
