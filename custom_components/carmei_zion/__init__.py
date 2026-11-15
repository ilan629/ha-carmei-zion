"""Carmei Zion Times: the weekly Carmei Zion shul times as Home Assistant sensors."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .coordinator import CarmeiZionConfigEntry, CarmeiZionCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: CarmeiZionConfigEntry) -> bool:
    """Set up Carmei Zion Times from a config entry."""
    coordinator = CarmeiZionCoordinator(hass, entry)
    await coordinator.async_load_saved()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # "Next Sunday Mincha" and "up to date" depend on the clock, not just on new data,
    # so re-evaluate the entities every minute (no download involved).
    # Must be an event-loop @callback: a plain lambda is run in a worker thread, and
    # writing entity state from there is rejected by Home Assistant.
    @callback
    def _async_tick(_now) -> None:
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_interval(hass, _async_tick, timedelta(minutes=1)))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CarmeiZionConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
