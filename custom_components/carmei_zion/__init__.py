"""Carmei Zion Times: the weekly Carmei Zion shul times as Home Assistant sensors."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
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
    entry.async_on_unload(
        async_track_time_interval(hass, lambda _now: coordinator.async_update_listeners(), timedelta(minutes=1))
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CarmeiZionConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
