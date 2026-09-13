"""Schemas for EEM Online setup and credential updates."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.eem_online.const import CONF_CONTRACT
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector

_USERNAME = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT, autocomplete="username"),
)
_PASSWORD = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD, autocomplete="current-password"),
)
_CONTRACT = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))


def get_user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build the initial setup form."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, vol.UNDEFINED)): _USERNAME,
            vol.Required(CONF_PASSWORD): _PASSWORD,
            vol.Required(CONF_CONTRACT, default=defaults.get(CONF_CONTRACT, vol.UNDEFINED)): _CONTRACT,
        },
    )


def get_credentials_schema(username: str) -> vol.Schema:
    """Build a form that updates credentials without changing the contract."""
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=username): _USERNAME,
            vol.Required(CONF_PASSWORD): _PASSWORD,
        },
    )


__all__ = ["get_credentials_schema", "get_user_schema"]
