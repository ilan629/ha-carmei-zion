"""Constants for the Carmei Zion Times integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "carmei_zion"
NAME: Final = "Carmei Zion Times"

DEFAULT_URL: Final = "https://ilan629.github.io/Carmei-Zion-Times/carmei-zion.json"
CONF_URL: Final = "url"

# The feed is a small static file on GitHub Pages; once an hour is plenty.
UPDATE_INTERVAL: Final = timedelta(hours=1)
REQUEST_TIMEOUT: Final = 20  # seconds

# Feed format versions this integration understands. A feed without
# "schema_version" is treated as version 1 (the original format).
SUPPORTED_SCHEMA_VERSION: Final = 1
DEFAULT_TIMEZONE: Final = "Asia/Jerusalem"

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.last_schedule"

ATTRIBUTION: Final = "Times as printed on the Carmei Zion weekly schedule"

# Shabbat rows on the flyer: key -> (entity name, which day, icon).
# Entity names match the owner's own setup, so entity ids come out the same
# (device "CZ" + "Friday Mincha" -> sensor.cz_friday_mincha).
SHABBAT_SENSORS: Final[dict[str, tuple[str, str, str]]] = {
    "mincha_kabbalat_shabbat_early": ("Friday Early Mincha", "friday", "mdi:weather-sunset"),
    "plag_hamincha": ("Friday Plag HaMincha", "friday", "mdi:weather-sunset-down"),
    "mincha_kabbalat_shabbat": ("Friday Mincha", "friday", "mdi:weather-sunset"),
    "shkia": ("Friday Shkia", "friday", "mdi:weather-sunset-down"),
    "shacharit_1": ("Shabbat Shacharit A", "saturday", "mdi:book-open-variant"),
    "shacharit_2": ("Shabbat Shacharit B", "saturday", "mdi:book-open-variant"),
    "shacharit_3": ("Shabbat Shacharit C", "saturday", "mdi:book-open-variant"),
    "sof_zman_shma": ("Shabbat Sof Zman Shma", "saturday", "mdi:clock-alert-outline"),
    "kids_learning_1": ("Shabbat Kids Learning 1", "saturday", "mdi:human-male-child"),
    "kids_learning_2": ("Shabbat Kids Learning 2", "saturday", "mdi:human-male-child"),
    "daf_yomi": ("Shabbat Daf Yomi", "saturday", "mdi:book-education"),
    "mincha_shabbat": ("Shabbat Mincha", "saturday", "mdi:book-open-variant"),
    "maariv_motzei_shabbat": ("Shabbat Maariv", "saturday", "mdi:weather-night"),
}

# Weekday table: key -> (entity name suffix, weekdays it can apply to, icon).
DAY_NAMES: Final = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAY_SENSORS: Final[dict[str, tuple[str, list[str], str]]] = {
    "shacharit_1": ("Shacharit A", DAY_NAMES, "mdi:weather-sunny"),
    "shacharit_2": ("Shacharit B", DAY_NAMES, "mdi:weather-sunny"),
    "mincha": ("Mincha", DAY_NAMES[:5], "mdi:white-balance-sunny"),
    "maariv": ("Maariv", DAY_NAMES[:5], "mdi:weather-night"),
}
