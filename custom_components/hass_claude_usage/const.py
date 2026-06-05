"""Constants for Claude Usage integration."""

DOMAIN = "hass_claude_usage"

# OAuth
OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
OAUTH_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
OAUTH_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
OAUTH_REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
OAUTH_SCOPES = "org:create_api_key user:profile user:inference"

# API
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
PROFILE_API_URL = "https://api.anthropic.com/api/oauth/profile"
API_BETA_HEADER = "oauth-2025-04-20"
CODEX_USAGE_API_URL = "https://chatgpt.com/backend-api/wham/usage"
CODEX_OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"
CODEX_OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

# Defaults
DEFAULT_UPDATE_INTERVAL = 300  # seconds

# Config keys
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_AT = "expires_at"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ACCOUNT_ID = "account_id"
CONF_ACCOUNT_NAME = "account_name"
CONF_ACCOUNT_EMAIL = "account_email"
CONF_SUBSCRIPTION_LEVEL = "subscription_level"
CONF_CODEX_ACCESS_TOKEN = "codex_access_token"
CONF_CODEX_REFRESH_TOKEN = "codex_refresh_token"
CONF_CODEX_ACCOUNT_ID = "codex_account_id"

# Sensor definitions: (key, name, unit, icon, device_class)
# key corresponds to a path in the parsed usage data dict
CLAUDE_SENSOR_DEFINITIONS = [
    ("session_usage_percent", "Session Usage", "%", "mdi:timer-sand", None),
    (
        "session_reset_time",
        "Session Reset Time",
        None,
        "mdi:timer-refresh",
        "timestamp",
    ),
    ("week_usage_percent", "Week Usage", "%", "mdi:calendar-week", None),
    ("week_usage_pace", "Week Usage Pace", "%", "mdi:speedometer", None),
    ("week_reset_time", "Weekly Reset Time", None, "mdi:calendar-clock", "timestamp"),
    (
        "week_sonnet_usage_percent",
        "Weekly Sonnet Usage",
        "%",
        "mdi:calendar-week",
        None,
    ),
    (
        "week_sonnet_reset_time",
        "Weekly Sonnet Reset Time",
        None,
        "mdi:calendar-clock",
        "timestamp",
    ),
    ("extra_usage_enabled", "Extra Usage Enabled", None, "mdi:toggle-switch", None),
    ("extra_usage_percent", "Extra Usage", "%", "mdi:credit-card", None),
    (
        "extra_usage_credits",
        "Extra Usage Credits",
        "credits",
        "mdi:credit-card-outline",
        None,
    ),
    (
        "extra_usage_limit",
        "Extra Usage Limit",
        "credits",
        "mdi:credit-card-settings",
        None,
    ),
    ("api_error", "API Error", "errors", "mdi:alert-circle", None),
]

CODEX_SENSOR_DEFINITIONS = [
    ("primary_used_percent", "Codex 5h Used", "%", "mdi:timer-sand", None),
    ("primary_remaining_percent", "Codex 5h Remaining", "%", "mdi:timer-outline", None),
    ("primary_reset_time", "Codex 5h Reset", None, "mdi:clock-outline", None),
    ("secondary_used_percent", "Codex Weekly Used", "%", "mdi:calendar-week", None),
    (
        "secondary_remaining_percent",
        "Codex Weekly Remaining",
        "%",
        "mdi:calendar-check",
        None,
    ),
    ("secondary_reset_time", "Codex Weekly Reset", None, "mdi:calendar-clock", None),
    ("credits_balance", "Codex Credits", "credits", "mdi:cash", None),
    ("plan", "Codex Plan", None, "mdi:account-badge", None),
    ("rate_limit_reached_type", "Codex Limit Status", None, "mdi:alert-circle", None),
]

SENSOR_DEFINITIONS = CLAUDE_SENSOR_DEFINITIONS + CODEX_SENSOR_DEFINITIONS
