"""Constants for the Enaro Shopping integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "enaro_shopping"

CONF_API_BASE_URL = "api_base_url"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

DEFAULT_API_BASE_URL = "https://api.think-smarter.eu"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

PLATFORMS = ["todo"]
