"""Fetches the public Carmei Zion feed and keeps the last good schedule."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_URL, DOMAIN, REQUEST_TIMEOUT, STORAGE_KEY, STORAGE_VERSION, UPDATE_INTERVAL
from .schedule import FeedError, Schedule, TestDataError, parse_feed

_LOGGER = logging.getLogger(__name__)


@dataclass
class CarmeiZionData:
    """What the entities read."""

    schedule: Schedule | None
    fetched_at: datetime | None  # when the schedule in use was last downloaded
    last_error: str | None  # why the latest refresh wasn't used, if it wasn't


type CarmeiZionConfigEntry = ConfigEntry[CarmeiZionCoordinator]


async def fetch_feed(hass: HomeAssistant, url: str) -> dict[str, Any]:
    """Download the feed JSON (raises aiohttp/asyncio errors or FeedError)."""
    session = async_get_clientsession(hass)
    async with asyncio.timeout(REQUEST_TIMEOUT):
        # Cache-busting header so we don't get a stale copy from GitHub's CDN for long.
        resp = await session.get(url, headers={"Cache-Control": "no-cache"})
        resp.raise_for_status()
        data = await resp.json(content_type=None)
    if not isinstance(data, dict):
        raise FeedError("feed is not a JSON object")
    return data


class CarmeiZionCoordinator(DataUpdateCoordinator[CarmeiZionData]):
    """Hourly refresh. A failed or unusable refresh never throws away good data.

    The last good feed is saved to disk, so after a restart without internet
    (e.g. on Shabbat) the sensors still have this week's times.
    """

    config_entry: CarmeiZionConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CarmeiZionConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.url: str = entry.data[CONF_URL]
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")
        self._schedule: Schedule | None = None
        self._fetched_at: datetime | None = None

    async def async_load_saved(self) -> None:
        """Load the last good schedule saved on disk, if any."""
        saved = await self._store.async_load()
        if not saved:
            return
        try:
            self._schedule = parse_feed(saved["feed"])
            self._fetched_at = dt_util.parse_datetime(saved.get("fetched_at") or "")
        except (FeedError, KeyError, TypeError) as err:
            _LOGGER.debug("Ignoring saved schedule: %s", err)

    async def _async_update_data(self) -> CarmeiZionData:
        try:
            raw = await fetch_feed(self.hass, self.url)
            schedule = parse_feed(raw)
        except TestDataError as err:
            return self._keep(str(err), level=logging.INFO)
        except FeedError as err:
            return self._keep(f"feed not usable: {err}")
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            return self._keep(f"couldn't download the feed: {err or type(err).__name__}")

        # Never go backwards to an older week (e.g. a stale CDN copy).
        if self._schedule and schedule.shabbat_date < self._schedule.shabbat_date:
            return self._keep(f"feed is older ({schedule.shabbat_date}) than the saved schedule")

        now = dt_util.utcnow()
        if raw != (self._schedule.raw if self._schedule else None):
            await self._store.async_save({"feed": raw, "fetched_at": now.isoformat()})
            _LOGGER.info("Carmei Zion schedule for %s (%s)", schedule.shabbat_date, schedule.parasha)
        self._schedule, self._fetched_at = schedule, now
        return CarmeiZionData(schedule, now, None)

    def _keep(self, reason: str, level: int = logging.WARNING) -> CarmeiZionData:
        """Keep using the last good schedule; only fail if there has never been one."""
        if self._schedule is None:
            raise UpdateFailed(reason)
        _LOGGER.log(level, "Keeping the saved Carmei Zion schedule: %s", reason)
        return CarmeiZionData(self._schedule, self._fetched_at, reason)
