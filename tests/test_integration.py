"""End-to-end tests inside a real Home Assistant test instance."""

from __future__ import annotations

import json
from pathlib import Path

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.carmei_zion.const import CONF_URL, DEFAULT_URL, DOMAIN, UPDATE_INTERVAL

FEED = json.loads((Path(__file__).parent / "feed_bereshit.json").read_text(encoding="utf-8"))
THURSDAY_NIGHT = "2026-10-08T21:00:00+03:00"


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    e = MockConfigEntry(domain=DOMAIN, title="Carmei Zion Times", data={CONF_URL: DEFAULT_URL}, unique_id=DEFAULT_URL)
    e.add_to_hass(hass)
    return e


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config.async_set_time_zone("Europe/London")  # the friend's HA zone shouldn't matter
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_config_flow_one_click(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(DEFAULT_URL, json=FEED)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: DEFAULT_URL})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: DEFAULT_URL}

    # A second one is refused.
    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    again = await hass.config_entries.flow.async_configure(again["flow_id"], {CONF_URL: DEFAULT_URL})
    assert again["type"] is FlowResultType.ABORT


async def test_config_flow_errors(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(DEFAULT_URL, status=404)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: DEFAULT_URL})
    assert result["errors"] == {"base": "cannot_connect"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: "http://example.com/x.json"})
    assert result["errors"] == {CONF_URL: "https_only"}


@pytest.mark.freeze_time(THURSDAY_NIGHT)
async def test_sensors(hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(DEFAULT_URL, json=FEED)
    await _setup(hass, entry)

    def state(eid: str) -> str:
        st = hass.states.get(eid)
        assert st is not None, f"{eid} missing"
        return st.state

    # Same entity ids as the owner's own setup; UTC states, Israel times.
    assert state("sensor.cz_friday_candle_lighting") == "2026-10-09T14:56:00+00:00"
    assert hass.states.get("sensor.cz_friday_candle_lighting").attributes["time"] == "17:56"
    assert state("sensor.cz_friday_mincha") == "2026-10-09T15:01:00+00:00"
    assert state("sensor.cz_shabbat_shacharit_a") == "2026-10-10T04:00:00+00:00"
    assert state("sensor.cz_tzeit_shabbat") == "2026-10-10T15:52:00+00:00"
    assert state("sensor.cz_sunday_shacharit_a") == "2026-10-11T03:10:00+00:00"
    assert state("sensor.cz_friday_plag_hamincha") == "unknown"  # not on this flyer
    assert state("sensor.cz_parasha") == "שבת פרשת בראשית"
    assert state("binary_sensor.cz_schedule_up_to_date") == "on"


async def test_test_data_never_replaces_real_times(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(THURSDAY_NIGHT)
    aioclient_mock.get(DEFAULT_URL, json=FEED)
    await _setup(hass, entry)

    aioclient_mock.clear_requests()
    aioclient_mock.get(DEFAULT_URL, json=dict(FEED, test=True, candle_lighting="19:05", parasha="TEST"))
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.cz_friday_candle_lighting").state == "2026-10-09T14:56:00+00:00"
    assert hass.states.get("sensor.cz_parasha").state == "שבת פרשת בראשית"


async def test_offline_restart_uses_saved_schedule(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    """Shabbat scenario: HA restarts without internet and still has this week's times."""
    freezer.move_to(THURSDAY_NIGHT)
    aioclient_mock.get(DEFAULT_URL, json=FEED)
    await _setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)

    aioclient_mock.clear_requests()
    aioclient_mock.get(DEFAULT_URL, exc=TimeoutError())
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.cz_friday_candle_lighting").state == "2026-10-09T14:56:00+00:00"
    assert hass.states.get("sensor.cz_last_updated").attributes["last_problem"].startswith("couldn't download")


async def test_no_internet_and_nothing_saved_retries_setup(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(DEFAULT_URL, exc=TimeoutError())
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.SETUP_RETRY


@pytest.mark.freeze_time("2026-10-11T09:00:00+03:00")
async def test_up_to_date_turns_off_in_a_new_week(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(DEFAULT_URL, json=FEED)
    await _setup(hass, entry)
    assert hass.states.get("binary_sensor.cz_schedule_up_to_date").state == "off"
