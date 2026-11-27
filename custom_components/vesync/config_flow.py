"""Config flow for VeSync integration."""

from __future__ import annotations

from typing import Any

import httpx
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.httpx_client import get_async_client
from py_vesync import AsyncVeSyncClient, VeSyncAPIError, VeSyncAuthError

from .const import (
    CONF_ACCOUNT_ID,
    CONF_REGION,
    CONF_TERMINAL_ID,
    CONF_TOKEN,
    DEFAULT_REGION,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION, default=DEFAULT_REGION): vol.In(["EU", "US"]),
    }
)


class VeSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for VeSync."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            region = user_input[CONF_REGION]

            client = AsyncVeSyncClient(
                region=region,
                http_client=get_async_client(self.hass),
            )
            try:
                await client.login(email, password)
            except VeSyncAuthError:
                errors["base"] = "invalid_auth"
            except (VeSyncAPIError, httpx.HTTPError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                session = client.export_session()
                unique_id = session.get("account_id") or email.lower()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_REGION: session["region"],
                        CONF_TOKEN: session["token"],
                        CONF_ACCOUNT_ID: session["account_id"],
                        CONF_TERMINAL_ID: session["terminal_id"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
