"""Claude Usage integration for Home Assistant."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BETA_HEADER,
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    CONF_UPDATE_INTERVAL,
    CODEX_USAGE_API_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    OAUTH_CLIENT_ID,
    OAUTH_TOKEN_URL,
    PROFILE_API_URL,
    USAGE_API_URL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type ClaudeUsageConfigEntry = ConfigEntry[ClaudeUsageCoordinator]


async def async_migrate_entry(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> bool:
    """Migrate an old config entry to the current version.

    v1 entries were keyed by the static DOMAIN string (and, on installs created
    after multi-account support landed, by email). v2 keys each entry by a
    stable per-account identifier so the duplicate-account check works for
    installs that predate multi-account support, without requiring a reauth.

    Migration approach contributed by @thematrixdev in #9.
    """
    if entry.version > 1:
        return True

    _LOGGER.debug("Migrating Claude Usage config entry %s from v1 to v2", entry.entry_id)
    account_id = await _resolve_account_id(hass, entry)
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_ACCOUNT_ID: account_id},
        unique_id=account_id,
        version=2,
    )
    _LOGGER.info("Migrated Claude Usage config entry to v2 (account_id=%s)", account_id)
    return True


async def _resolve_account_id(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> str:
    """Resolve a stable account id during migration.

    Tries the stored access token, refreshing once on a 401. Falls back to the
    entry_id as a sentinel when the account cannot be identified; a later reauth
    replaces the sentinel with the real account id.
    """
    session = aiohttp_client.async_get_clientsession(hass)
    access_token = entry.data.get(CONF_ACCESS_TOKEN)

    for attempt in ("current", "refreshed"):
        if not access_token:
            break
        try:
            resp = await session.get(
                PROFILE_API_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "anthropic-beta": API_BETA_HEADER,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            )
            if resp.ok:
                account = (await resp.json()).get("account") or {}
                account_id = account.get("uuid") or account.get("id") or account.get("email")
                if account_id:
                    return account_id
                break
            # An expired token returns 401 — refresh once and retry.
            if resp.status == 401 and attempt == "current":
                access_token = await _refresh_token_for_migration(hass, session, entry)
                continue
            break
        except aiohttp.ClientError:
            _LOGGER.warning("Profile fetch failed during migration (attempt=%s)", attempt)
            break

    _LOGGER.warning(
        "Migration could not identify the account; using entry_id as a placeholder. "
        "Re-authenticate the entry to assign its real account id."
    )
    return entry.entry_id


async def _refresh_token_for_migration(
    hass: HomeAssistant,
    session: aiohttp.ClientSession,
    entry: ClaudeUsageConfigEntry,
) -> str | None:
    """Refresh the access token during migration; persist and return it, or None."""
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
    if not refresh_token:
        return None
    try:
        resp = await session.post(
            OAUTH_TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": OAUTH_CLIENT_ID,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        )
        if not resp.ok:
            return None
        token_data = await resp.json()
    except aiohttp.ClientError:
        _LOGGER.warning("Token refresh failed during migration")
        return None

    new_token = token_data.get("access_token")
    if not new_token:
        return None
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_ACCESS_TOKEN: new_token,
            CONF_REFRESH_TOKEN: token_data.get("refresh_token", refresh_token),
            CONF_EXPIRES_AT: time.time() + token_data.get("expires_in", 3600),
        },
    )
    return new_token


async def async_setup_entry(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> bool:
    """Set up Claude Usage from a config entry."""
    _migrate_codex_options_to_data(hass, entry)
    coordinator = ClaudeUsageCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
    """Handle options update."""
    coordinator: ClaudeUsageCoordinator = entry.runtime_data
    interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator.update_interval = timedelta(seconds=interval)


def _migrate_codex_options_to_data(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
    """Move Codex credentials out of options if an earlier build stored them there."""
    option_keys = {CONF_CODEX_ACCESS_TOKEN, CONF_CODEX_ACCOUNT_ID}
    if not option_keys.intersection(entry.options):
        return

    data = dict(entry.data)
    options = dict(entry.options)
    for key in option_keys:
        value = options.pop(key, None)
        if value:
            data[key] = value

    hass.config_entries.async_update_entry(entry, data=data, options=options)


class ClaudeUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Claude usage data."""

    config_entry: ClaudeUsageConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
            always_update=False,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch usage data from the API."""
        await self._ensure_valid_token()

        access_token = self.config_entry.data[CONF_ACCESS_TOKEN]
        headers = {
            "Authorization": f"Bearer {access_token}",
            "anthropic-beta": API_BETA_HEADER,
        }

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.get(
                USAGE_API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            )
            if resp.status == 401:
                raise ConfigEntryAuthFailed("Authentication failed - token may be invalid")
            resp.raise_for_status()
            raw = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching usage data: {err}") from err

        data = _parse_usage(raw)
        data.update(await self._async_fetch_codex_usage())
        return data

    async def _async_fetch_codex_usage(self) -> dict[str, Any]:
        """Fetch Codex usage data when a Codex token is configured."""
        access_token = self.config_entry.data.get(CONF_CODEX_ACCESS_TOKEN)
        if not access_token:
            return {}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "hass-claude-usage",
        }
        account_id = self.config_entry.data.get(CONF_CODEX_ACCOUNT_ID)
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.get(
                CODEX_USAGE_API_URL,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            )
            if resp.status == 401:
                _LOGGER.warning("Codex usage authentication failed")
                return {}
            resp.raise_for_status()
            raw = await resp.json()
        except (aiohttp.ClientError, ValueError):
            _LOGGER.exception("Error fetching Codex usage data")
            return {}

        if not isinstance(raw, dict):
            _LOGGER.warning("Codex usage response was not a JSON object")
            return {}

        try:
            return _parse_codex_usage(raw)
        except (TypeError, ValueError):
            _LOGGER.exception("Error parsing Codex usage data")
            return {}

    async def _ensure_valid_token(self) -> None:
        """Refresh the access token if expired."""
        expires_at = self.config_entry.data.get(CONF_EXPIRES_AT, 0)
        if time.time() < expires_at - 60:
            return

        refresh_token = self.config_entry.data.get(CONF_REFRESH_TOKEN)
        if not refresh_token:
            raise ConfigEntryAuthFailed("No refresh token available")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": OAUTH_CLIENT_ID,
        }

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.post(
                OAUTH_TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            )
            if not resp.ok:
                raise ConfigEntryAuthFailed(f"Token refresh failed ({resp.status})")
            token_data = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Token refresh request failed: {err}") from err

        if "access_token" not in token_data:
            raise ConfigEntryAuthFailed("Token refresh response missing access_token")

        new_data = {
            **self.config_entry.data,
            CONF_ACCESS_TOKEN: token_data["access_token"],
            CONF_REFRESH_TOKEN: token_data.get("refresh_token", refresh_token),
            CONF_EXPIRES_AT: time.time() + token_data.get("expires_in", 3600),
        }
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)


def _parse_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse raw API response into flat sensor data dict."""
    data: dict[str, Any] = {}

    five_hour = raw.get("five_hour")
    if five_hour:
        data["session_usage_percent"] = five_hour.get("utilization")
        data["session_reset_time"] = five_hour.get("resets_at")

    seven_day = raw.get("seven_day")
    if seven_day:
        utilization = seven_day.get("utilization")
        reset_time = seven_day.get("resets_at")
        data["week_usage_percent"] = utilization
        data["week_reset_time"] = reset_time
        if utilization is not None and reset_time:
            try:
                reset_dt = datetime.fromisoformat(reset_time)
                now = datetime.now(UTC)
                week_seconds = 7 * 24 * 60 * 60
                elapsed = week_seconds - (reset_dt - now).total_seconds()
                percent_elapsed = (elapsed / week_seconds) * 100
                data["week_usage_pace"] = round(utilization - percent_elapsed, 1)
            except (ValueError, TypeError):
                pass

    seven_day_sonnet = raw.get("seven_day_sonnet")
    if seven_day_sonnet:
        data["week_sonnet_usage_percent"] = seven_day_sonnet.get("utilization")
        data["week_sonnet_reset_time"] = seven_day_sonnet.get("resets_at")

    # Overage/extra usage. The older API exposes this under "extra_usage" with
    # credits in minor currency units; the newer API (mid-2026) moved it to a
    # top-level "spend" object. Read whichever is enabled.
    extra = raw.get("extra_usage")
    spend = raw.get("spend")
    if extra and extra.get("is_enabled"):
        divisor = 10 ** extra.get("decimal_places", 2)
        used = extra.get("used_credits")
        limit = extra.get("monthly_limit")
        data["extra_usage_enabled"] = True
        data["extra_usage_percent"] = extra.get("utilization")
        data["extra_usage_credits"] = used / divisor if used is not None else None
        data["extra_usage_limit"] = limit / divisor if limit is not None else None
    elif spend and spend.get("enabled"):
        # In the "spend" schema both "used" and "limit" are money objects of the
        # form {"amount_minor": int, "currency": str, "exponent": int}; "limit"
        # may be null when no cap is set. "percent" is already 0-100.
        used = spend.get("used") or {}
        limit = spend.get("limit") or {}
        used_divisor = 10 ** used.get("exponent", 2)
        limit_divisor = 10 ** limit.get("exponent", 2)
        amount = used.get("amount_minor")
        limit_amount = limit.get("amount_minor")
        data["extra_usage_enabled"] = True
        data["extra_usage_percent"] = spend.get("percent")
        data["extra_usage_credits"] = amount / used_divisor if amount is not None else None
        data["extra_usage_limit"] = (
            limit_amount / limit_divisor if limit_amount is not None else None
        )
    elif extra is not None or spend is not None:
        data["extra_usage_enabled"] = False

    return data


def _normalize_codex_window(window: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize one Codex usage window."""
    if not isinstance(window, dict):
        return None

    used_percent = window.get("used_percent", 0)
    try:
        used_percent = float(used_percent)
    except (TypeError, ValueError):
        used_percent = 0

    return {
        "used_percent": used_percent,
        "remaining_percent": max(0, 100 - used_percent),
        "reset_at": window.get("reset_at"),
    }


def _first_some(*values: Any) -> Any:
    """Return the first non-null value."""
    return next((value for value in values if value is not None), None)


def _format_codex_reset_time(epoch_seconds: Any, include_date: bool) -> str | None:
    """Format Codex reset time like the MQTT bridge sensors."""
    if not epoch_seconds:
        return None

    try:
        reset = datetime.fromtimestamp(float(epoch_seconds), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None

    if include_date:
        return reset.strftime("%d/%m - %H:%M")
    return reset.strftime("%H:%M")


def _normalize_codex_limit_status(status: Any) -> str:
    """Normalize the Codex rate limit status."""
    if not status or str(status).lower() == "unknown":
        return "OK"
    return str(status)


def _parse_codex_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse raw Codex API response into flat sensor data dict."""
    data: dict[str, Any] = {}
    rate_limit = raw.get("rate_limit") or raw.get("rateLimits") or {}
    if not isinstance(rate_limit, dict):
        rate_limit = {}
    primary = _normalize_codex_window(
        _first_some(rate_limit.get("primary_window"), rate_limit.get("primary"))
    )
    secondary = _normalize_codex_window(
        _first_some(rate_limit.get("secondary_window"), rate_limit.get("secondary"))
    )
    credits = raw.get("credits") or {}
    if not isinstance(credits, dict):
        credits = {}
    rate_limit_reached_type = raw.get("rate_limit_reached_type")
    if isinstance(rate_limit_reached_type, dict):
        rate_limit_reached_type = rate_limit_reached_type.get("kind")

    plan = raw.get("plan_type") or raw.get("planType")
    if plan is not None:
        data["plan"] = plan

    if primary:
        data["primary_used_percent"] = primary["used_percent"]
        data["primary_remaining_percent"] = primary["remaining_percent"]
        reset_time = _format_codex_reset_time(primary.get("reset_at"), False)
        if reset_time is not None:
            data["primary_reset_time"] = reset_time

    if secondary:
        data["secondary_used_percent"] = secondary["used_percent"]
        data["secondary_remaining_percent"] = secondary["remaining_percent"]
        reset_time = _format_codex_reset_time(secondary.get("reset_at"), True)
        if reset_time is not None:
            data["secondary_reset_time"] = reset_time

    credits_balance = credits.get("balance")
    if credits_balance is not None:
        data["credits_balance"] = credits_balance

    if rate_limit_reached_type is not None:
        data["rate_limit_reached_type"] = _normalize_codex_limit_status(
            rate_limit_reached_type
        )

    return data
