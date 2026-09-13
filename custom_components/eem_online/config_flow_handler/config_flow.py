"""Config flow for EEM Online."""

from typing import Any

from custom_components.eem_online.api import (
    EemOnlineApiClientAuthenticationError,
    EemOnlineApiClientCommunicationError,
    EemOnlineApiClientError,
)
from custom_components.eem_online.const import CONF_CONTRACT, DOMAIN, LOGGER
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .schemas import get_credentials_schema, get_user_schema
from .validators import validate_connection


class EemOnlineConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one EEM login and one contract."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Create an entry after validating its EEM access."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _normalize(user_input)
            contract = user_input[CONF_CONTRACT]
            if not contract.isdigit():
                errors[CONF_CONTRACT] = "invalid_contract"
            else:
                await self.async_set_unique_id(contract)
                self._abort_if_unique_id_configured()
                errors = await self._async_validate(user_input, contract)
                if not errors:
                    return self.async_create_entry(title=f"EEM Online {contract}", data=user_input)

        return self.async_show_form(step_id="user", data_schema=get_user_schema(user_input), errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> config_entries.ConfigFlowResult:
        """Start reauthentication for an existing entry."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Validate and save replacement credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _normalize(user_input)
            errors = await self._async_validate(user_input, entry.data[CONF_CONTRACT])
            if not errors:
                await self.async_set_unique_id(entry.unique_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=get_credentials_schema(entry.data[CONF_USERNAME]),
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Update credentials while preserving the contract and statistic ID."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _normalize(user_input)
            errors = await self._async_validate(user_input, entry.data[CONF_CONTRACT])
            if not errors:
                await self.async_set_unique_id(entry.unique_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_credentials_schema(entry.data[CONF_USERNAME]),
            errors=errors,
        )

    async def _async_validate(self, user_input: dict[str, Any], contract: str) -> dict[str, str]:
        """Map EEM validation failures to form errors."""
        try:
            await validate_connection(
                self.hass,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                contract,
            )
        except EemOnlineApiClientAuthenticationError:
            return {"base": "invalid_auth"}
        except EemOnlineApiClientCommunicationError:
            return {"base": "cannot_connect"}
        except EemOnlineApiClientError:
            return {"base": "invalid_response"}
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected exception during EEM setup")
            return {"base": "unknown"}
        return {}


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    """Strip identifiers while preserving the password exactly."""
    normalized = dict(user_input)
    normalized[CONF_USERNAME] = str(normalized[CONF_USERNAME]).strip()
    if CONF_CONTRACT in normalized:
        normalized[CONF_CONTRACT] = str(normalized[CONF_CONTRACT]).strip()
    return normalized


__all__ = ["EemOnlineConfigFlowHandler"]
