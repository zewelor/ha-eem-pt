"""Validate EEM Online credentials and the configured contract response."""

from typing import TYPE_CHECKING

from custom_components.eem_online.api import EemOnlineApiClient
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def validate_connection(hass: HomeAssistant, username: str, password: str, contract: str) -> None:
    """Authenticate and fetch the configured contract's weekly summary."""
    client = EemOnlineApiClient(username, password, async_get_clientsession(hass))
    await client.async_get_weekly_summary(contract)


__all__ = ["validate_connection"]
