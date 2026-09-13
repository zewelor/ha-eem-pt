"""Tests for the EEM Online HTTP client."""

from datetime import date
import re

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker, AiohttpClientMockResponse
from yarl import URL

from custom_components.eem_online.api import (
    EemOnlineApiClient,
    EemOnlineApiClientAuthenticationError,
    EemOnlineApiClientCommunicationError,
    EemOnlineApiClientError,
)
from custom_components.eem_online.const import BASE_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

SUMMARY_URL = f"{BASE_URL}/proxy.ashx?proxy-WS3BaseURL/api/sm/leituras/456/resumo/ultimasemana"
LOGIN_URL = f"{BASE_URL}/umbraco/surface/Auth/Auth"
READINGS_URL_PAGE_1 = URL(
    f"{BASE_URL}/proxy.ashx?proxy-WS3BaseURL/api/sm/leituras/456/leituras"
    "%3FPageNumber%3D1%26RowsPerPage%3D100%26OrderBy%3DData%26OrderType%3D1"
    "%26data%3D2026-08-01%252000%253A00%26data2%3D2026-08-30%252023%253A59",
    encoded=True,
)
READINGS_URL_PAGE_2 = URL(str(READINGS_URL_PAGE_1).replace("PageNumber%3D1", "PageNumber%3D2"), encoded=True)
START = date(2026, 8, 1)
END = date(2026, 8, 30)


def _exact_url(url: str | URL) -> re.Pattern[str]:
    return re.compile(f"^{re.escape(str(url))}$")


async def test_login_and_weekly_summary(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The client pads numeric usernames and sends the returned token."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(_exact_url(SUMMARY_URL), json={"consumos": []})
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    assert await client.async_get_weekly_summary("456") == {"consumos": []}
    assert aioclient_mock.mock_calls[0][2] == {"Username": "0000000123", "Password": "secret"}
    assert aioclient_mock.mock_calls[1][3] == {"x-auth-token": "token"}


async def test_invalid_login(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The observed HTTP 203 login response is an authentication failure."""
    aioclient_mock.post(LOGIN_URL, status=203)
    client = EemOnlineApiClient("user", "wrong", async_get_clientsession(hass))
    with pytest.raises(EemOnlineApiClientAuthenticationError):
        await client.async_get_weekly_summary("456")


async def test_meter_readings_reuse_token_and_exact_query(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Summary and readings share one token and use the PoC query encoding."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(_exact_url(SUMMARY_URL), json={"consumos": []})
    record = {"data": "2026-08-30T00:00:00", "totalRegistadores": 123.0}
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), json={"data": [record], "pageCount": 1})
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    await client.async_get_weekly_summary("456")
    assert await client.async_get_meter_readings("456", START, END) == [record]
    assert [call[0] for call in aioclient_mock.mock_calls].count("POST") == 1
    assert aioclient_mock.mock_calls[-1][1] == READINGS_URL_PAGE_1
    assert aioclient_mock.mock_calls[-1][3] == {"x-auth-token": "token"}


async def test_meter_readings_fetch_all_pages(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """The client returns records only after every advertised page succeeds."""
    aioclient_mock.post(LOGIN_URL, text="token")
    first = {"data": "2026-08-29T00:00:00", "totalRegistadores": 122.0}
    second = {"data": "2026-08-30T00:00:00", "totalRegistadores": 123.0}
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), json={"data": [first], "pageCount": 2})
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_2), json={"data": [second], "pageCount": 2})
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    assert await client.async_get_meter_readings("456", START, END) == [first, second]


async def test_meter_readings_reject_changed_page_count(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Every page must agree with the first page's advertised total."""
    aioclient_mock.post(LOGIN_URL, text="token")
    first = {"data": "2026-08-28T00:00:00", "totalRegistadores": 121.0}
    second = {"data": "2026-08-29T00:00:00", "totalRegistadores": 122.0}
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), json={"data": [first], "pageCount": 3})
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_2), json={"data": [second], "pageCount": 2})
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    with pytest.raises(EemOnlineApiClientError, match="inconsistent meter-reading pagination"):
        await client.async_get_meter_readings("456", START, END)


async def test_meter_readings_accept_empty_page(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A valid empty first page means that EEM has no readings yet."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), json={"data": [], "pageCount": 1})
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    assert await client.async_get_meter_readings("456", START, END) == []


async def test_meter_readings_accept_zero_page_count(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """An empty first page may report that the result has zero pages."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), json={"data": [], "pageCount": 0})
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    assert await client.async_get_meter_readings("456", START, END) == []


async def test_meter_readings_accept_no_content(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """HTTP 204 on the first page means that EEM has no readings yet."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), status=204)
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    assert await client.async_get_meter_readings("456", START, END) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"data": []},
        {"data": [], "pageCount": False},
        {"data": [{"data": "2026-08-30T00:00:00", "totalRegistadores": 123.0}], "pageCount": 0},
    ],
)
async def test_meter_readings_reject_invalid_pagination(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    payload: dict[str, object],
) -> None:
    """Missing or contradictory pagination metadata is invalid."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), json=payload)
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    with pytest.raises(EemOnlineApiClientError):
        await client.async_get_meter_readings("456", START, END)


async def test_meter_readings_do_not_return_partial_pages(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A later page failure fails the complete readings request."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(
        _exact_url(READINGS_URL_PAGE_1),
        json={"data": [{"data": "2026-08-29T00:00:00", "totalRegistadores": 122.0}], "pageCount": 2},
    )
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_2), status=500)
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    with pytest.raises(EemOnlineApiClientCommunicationError):
        await client.async_get_meter_readings("456", START, END)


async def test_meter_readings_reject_no_content_after_first_page(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """HTTP 204 after an advertised first page is an incomplete response."""
    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(
        _exact_url(READINGS_URL_PAGE_1),
        json={"data": [{"data": "2026-08-29T00:00:00", "totalRegistadores": 122.0}], "pageCount": 2},
    )
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_2), status=204)
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    with pytest.raises(EemOnlineApiClientError):
        await client.async_get_meter_readings("456", START, END)


async def test_meter_readings_reauthenticate_once(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A rejected shared token causes one login retry for readings."""
    request_count = 0

    async def readings_response(method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return AiohttpClientMockResponse(method, url, status=401)
        return AiohttpClientMockResponse(method, url, json={"data": [], "pageCount": 1})

    aioclient_mock.post(LOGIN_URL, text="token")
    aioclient_mock.get(_exact_url(READINGS_URL_PAGE_1), side_effect=readings_response)
    client = EemOnlineApiClient("123", "secret", async_get_clientsession(hass))

    assert await client.async_get_meter_readings("456", START, END) == []
    assert request_count == 2
    assert [call[0] for call in aioclient_mock.mock_calls].count("POST") == 2
