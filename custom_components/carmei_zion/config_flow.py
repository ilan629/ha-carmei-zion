"""Config flow: one click, the feed address is pre-filled."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_URL, DEFAULT_URL, DOMAIN, NAME
from .coordinator import fetch_feed
from .schedule import FeedError, TestDataError, parse_feed

_LOGGER = logging.getLogger(__name__)


class CarmeiZionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup dialog."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the feed address (defaults to the public Carmei Zion feed) and check it works."""
        errors: dict[str, str] = {}
        url = DEFAULT_URL
        if user_input is not None:
            url = user_input[CONF_URL].strip()
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            if not url.startswith("https://"):
                errors[CONF_URL] = "https_only"
            else:
                try:
                    parse_feed(await fetch_feed(self.hass, url))
                except TestDataError:
                    pass  # the feed works; it only holds test data right now
                except FeedError as err:
                    _LOGGER.warning("Carmei Zion feed at %s isn't usable: %s", url, err)
                    errors["base"] = "bad_feed"
                except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                    _LOGGER.warning("Couldn't reach the Carmei Zion feed at %s: %s", url, err)
                    errors["base"] = "cannot_connect"
                if not errors:
                    return self.async_create_entry(title=NAME, data={CONF_URL: url})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=url): str}),
            errors=errors,
        )
