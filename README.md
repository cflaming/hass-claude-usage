# Claude Usage - Home Assistant Integration

A custom Home Assistant integration that monitors your Claude (Anthropic) subscription usage.

![Claude Usage Screenshot](screenshot.jpg)

## Sensors

- **Session Usage** - Current 5-hour session utilization (%)
- **Session Reset Time** - When the session limit resets
- **Week Usage** - Current 7-day utilization, all models (%)
- **Weekly Reset Time** - When the weekly limit resets
- **Weekly Sonnet Usage** - Current 7-day Sonnet utilization (%)
- **Weekly Sonnet Reset Time** - When the Sonnet weekly limit resets
- **Extra Usage Enabled** - Whether extra usage is enabled
- **Extra Usage** - Extra usage utilization (%)
- **Extra Usage Credits** - Credits consumed this month
- **Extra Usage Limit** - Monthly credit limit
- **Codex 5h Used** - Current Codex 5-hour usage (%)
- **Codex 5h Remaining** - Current Codex 5-hour remaining (%)
- **Codex 5h Reset** - When the Codex 5-hour window resets
- **Codex Weekly Used** - Current Codex weekly usage (%)
- **Codex Weekly Remaining** - Current Codex weekly remaining (%)
- **Codex Weekly Reset** - When the Codex weekly window resets
- **Codex Credits** - Current Codex credits balance
- **Codex Plan** - Current Codex plan
- **Codex Limit Status** - Current Codex rate limit status

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
2. Restart Home Assistant
3. Install "Claude Usage"
4. Go to Settings → Devices & Services → Add Integration → "Claude Usage"
5. Follow the instructions

### Manual

1. Copy `custom_components/hass_claude_usage/` to your HA `custom_components/` directory
2. Restart Home Assistant
3. Add the integration via the UI

## Setup

The integration uses Anthropic's OAuth flow:

1. When adding the integration, you'll be shown an authorization URL
2. Open the URL in your browser and log in to your Anthropic account
3. After authorizing, you'll be redirected to a page with an authorization code
4. Copy the code and paste it into the Home Assistant config flow

## Options

- **Update interval** - How often to poll the usage API (default: 300 seconds, min: 60, max: 3600).
- **Codex access token** - Optional OpenAI/Codex bearer token used to populate Codex sensors.
- **Codex refresh token** - Optional OAuth refresh token used to renew stale Codex access tokens.
- **ChatGPT account ID** - Optional account ID for Codex usage requests.

Codex sensors are created with the integration but remain unavailable until a Codex access token is configured.
When a refresh token is configured, the integration refreshes a bearer token shortly before its JWT expiry and retries
once after an unauthorized usage response. Rotated access and refresh tokens are saved automatically.

### Codex credentials

On a machine where the Codex CLI is logged in, open `~/.codex/auth.json` (or
`$CODEX_HOME/auth.json`). Copy these values from its `tokens` object into the integration options:

```json
{
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "account_id": "..."
  }
}
```

- `access_token` goes in **Codex access token**.
- `refresh_token` goes in **Codex refresh token**.
- `account_id` goes in **ChatGPT account ID**.

The token fields are intentionally blank when reopening options. Leaving them blank preserves the stored values.
Treat `auth.json`, access tokens, and refresh tokens as passwords. Do not share or commit them.

## Dashboard

A pre-built dashboard is included in the `dashboards/` directory. To use it:

1. Go to Settings → Dashboards → Add Dashboard
2. Click the three-dot menu → "Edit Dashboard"
3. Click the three-dot menu again → "Raw configuration editor"
4. Copy the contents of `dashboards/claude_usage.yaml` and paste it
5. Click "Save"

Alternatively, you can manually add the cards to any existing dashboard by referencing the YAML file.

## Rate Limit

I have found Anthropic rate limits the usage API when you hit it too fast; usually a couple of dozen bursts in a minute is enough. The backoff time is around 24 hours, during which you won't be able to see your usage here, in Claude Code, or on https://claude.ai.  I recommend keeping the polling frequency at 300 :)

## Development

### Pre-commit Hook

Install the pre-commit hook to automatically format code before committing:

```bash
pip install pre-commit
pre-commit install
```

This will run black, isort, ruff, and other checks before each commit.

### Manual Formatting

```bash
pip install black isort ruff
black custom_components/hass_claude_usage/
isort custom_components/hass_claude_usage/
ruff check --fix custom_components/hass_claude_usage/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
