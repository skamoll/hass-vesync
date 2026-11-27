"""Constants for the VeSync integration."""

DOMAIN = "vesync"

CONF_REGION = "region"
CONF_TOKEN = "token"
CONF_ACCOUNT_ID = "account_id"
CONF_TERMINAL_ID = "terminal_id"

DEFAULT_REGION = "EU"
DEFAULT_STANDBY_INTERVAL = 10
DEFAULT_ACTIVE_INTERVAL = 5

PLATFORMS: list[str] = ["sensor", "binary_sensor", "image", "button", "update"]

EVENT_COOK_COMPLETED = "vesync_cook_completed"

SERVICE_START_COOK = "start_cook"
SERVICE_END_COOK = "end_cook"
SERVICE_SET_COOK_TIME = "set_cook_time"
SERVICE_SET_TEMP_UNIT = "set_temp_unit"
