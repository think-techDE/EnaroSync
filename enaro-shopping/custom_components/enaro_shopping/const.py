"""Constants for the Enaro integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "enaro_shopping"

CONF_API_BASE_URL = "api_base_url"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SENSOR_RULES = "sensor_rules"

CONF_RULE_ENABLED = "enabled"
CONF_RULE_ENTITY_ID = "entity_id"
CONF_RULE_HOUSEHOLD_ID = "household_id"
CONF_RULE_ID = "id"
CONF_RULE_IMPORTANT = "important"
CONF_RULE_MEMBER_ID = "member_id"
CONF_RULE_NOTES_TEMPLATE = "notes_template"
CONF_RULE_TARGET_STATE = "target_state"
CONF_RULE_TITLE_TEMPLATE = "title_template"

DATA_COORDINATOR = "coordinator"
DATA_SENSOR_RULE_MANAGER = "sensor_rule_manager"

DEFAULT_API_BASE_URL = "https://api.think-smarter.eu"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
DEFAULT_SENSOR_RULE_TARGET_STATE = "unavailable"
DEFAULT_SENSOR_RULE_TITLE_TEMPLATE = "{entity_name} pruefen"
DEFAULT_SENSOR_RULE_NOTES_TEMPLATE = (
    "Home Assistant hat {entity_name} ({entity_id}) am {triggered_at} "
    "im Zustand {state} erkannt."
)
SENSOR_RULE_DEBOUNCE_SECONDS = 300
SENSOR_RULE_RETRY_SECONDS = 300

PLATFORMS = ["todo"]
