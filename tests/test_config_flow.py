"""Tests for the EEM Online config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eem_online.api import EemOnlineApiClientAuthenticationError, EemOnlineApiClientCommunicationError
from custom_components.eem_online.const import CONF_CONTRACT, DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

USER_INPUT = {CONF_USERNAME: " 123 ", CONF_PASSWORD: "secret", CONF_CONTRACT: " 456 "}


@pytest.fixture(autouse=True)
def mock_setup_entry() -> Generator[AsyncMock]:
    """Keep config-flow tests focused on configuration, not runtime setup."""
    with patch("custom_components.eem_online.async_setup_entry", new_callable=AsyncMock, return_value=True) as setup:
        yield setup


async def test_user_flow_creates_one_contract(recorder_mock: object, hass: HomeAssistant) -> None:
    """Valid credentials and a numeric contract create an entry."""
    with patch(
        "custom_components.eem_online.config_flow_handler.config_flow.validate_connection",
        new_callable=AsyncMock,
    ) as validate:
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "EEM Online 456"
    assert result["data"] == {CONF_USERNAME: "123", CONF_PASSWORD: "secret", CONF_CONTRACT: "456"}
    validate.assert_awaited_once_with(hass, "123", "secret", "456")


async def test_duplicate_contract_aborts(
    recorder_mock: object,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """The contract number is the stable entry identity."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: "other", CONF_PASSWORD: "secret", CONF_CONTRACT: "123456"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_same_account_can_add_another_contract(
    recorder_mock: object,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """A login may be reused for a separate contract entry."""
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.eem_online.config_flow_handler.config_flow.validate_connection",
        new_callable=AsyncMock,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "123", CONF_PASSWORD: "secret", CONF_CONTRACT: "654321"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "EEM Online 654321"
    assert result["data"][CONF_CONTRACT] == "654321"


@pytest.mark.parametrize(
    ("error", "translation_key"),
    [
        (EemOnlineApiClientAuthenticationError("auth"), "invalid_auth"),
        (EemOnlineApiClientCommunicationError("network"), "cannot_connect"),
    ],
)
async def test_user_flow_reports_api_errors(
    recorder_mock: object,
    hass: HomeAssistant,
    error: Exception,
    translation_key: str,
) -> None:
    """Expected API failures return actionable form errors."""
    with patch(
        "custom_components.eem_online.config_flow_handler.config_flow.validate_connection",
        new_callable=AsyncMock,
        side_effect=error,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": translation_key}


async def test_reauth_preserves_contract(
    recorder_mock: object,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Reauthentication changes credentials without creating new Energy history."""
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.eem_online.config_flow_handler.config_flow.validate_connection",
        new_callable=AsyncMock,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id, "unique_id": config_entry.unique_id},
            data=config_entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "new-user", CONF_PASSWORD: "new-secret"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_CONTRACT] == "123456"
    assert config_entry.data[CONF_USERNAME] == "new-user"


async def test_reconfigure_does_not_expose_saved_password(
    recorder_mock: object,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """The reconfigure form must not send the stored password to the frontend."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    password_field = next(field for field in result["data_schema"].schema if field.schema == CONF_PASSWORD)
    assert not password_field.description
