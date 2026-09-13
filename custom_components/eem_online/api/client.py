"""Asynchronous client for the reverse-engineered EEM Online API."""

import asyncio
from collections.abc import Mapping
from datetime import date
from typing import Any
from urllib.parse import quote, urlencode

import aiohttp
from yarl import URL

from custom_components.eem_online.const import BASE_URL

REQUEST_TIMEOUT = 30
AUTH_FAILURE_STATUSES = {203, 401, 403}


class EemOnlineApiClientError(Exception):
    """Base exception for an invalid EEM response."""


class EemOnlineApiClientCommunicationError(EemOnlineApiClientError):
    """EEM could not be reached."""


class EemOnlineApiClientAuthenticationError(EemOnlineApiClientError):
    """EEM rejected the credentials or token."""


class EemOnlineApiClient:
    """Authenticate and fetch EEM consumption data."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self._username = username.zfill(10) if username.isdigit() else username
        self._password = password
        self._session = session
        self._token: str | None = None

    async def async_get_weekly_summary(self, contract: str) -> Mapping[str, Any]:
        """Return the weekly summary, renewing the token once if necessary."""
        url = f"{BASE_URL}/proxy.ashx?proxy-WS3BaseURL/api/sm/leituras/{contract}/resumo/ultimasemana"
        payload = await self._async_get_json(url)
        if payload is None:
            return {"consumos": None}
        if not isinstance(payload, Mapping) or "consumos" not in payload:
            raise EemOnlineApiClientError("EEM returned an unexpected weekly summary")
        return payload

    async def async_get_meter_readings(self, contract: str, start: date, end: date) -> list[Mapping[str, Any]]:
        """Return every meter-reading page for the inclusive date range."""
        readings: list[Mapping[str, Any]] = []
        page = 1
        expected_page_count: int | None = None
        while True:
            query = urlencode(
                {
                    "PageNumber": page,
                    "RowsPerPage": 100,
                    "OrderBy": "Data",
                    "OrderType": 1,
                    "data": f"{start.isoformat()} 00:00",
                    "data2": f"{end.isoformat()} 23:59",
                },
                quote_via=quote,
            )
            url = (
                f"{BASE_URL}/proxy.ashx?proxy-WS3BaseURL/api/sm/leituras/{contract}/leituras"
                f"{quote(f'?{query}', safe='')}"
            )
            payload = await self._async_get_json(url)
            if payload is None:
                if page == 1:
                    return []
                raise EemOnlineApiClientError("EEM returned an incomplete meter-reading response")
            if not isinstance(payload, Mapping):
                raise EemOnlineApiClientError("EEM returned invalid meter-reading pagination")

            rows = payload.get("data")
            page_count = payload.get("pageCount")
            if not isinstance(rows, list) or not isinstance(page_count, int) or isinstance(page_count, bool):
                raise EemOnlineApiClientError("EEM returned invalid meter-reading pagination")
            if page == 1 and page_count == 0 and not rows:
                return []
            if expected_page_count is None:
                expected_page_count = page_count
            elif page_count != expected_page_count:
                raise EemOnlineApiClientError("EEM returned inconsistent meter-reading pagination")
            if expected_page_count < page:
                raise EemOnlineApiClientError("EEM returned invalid meter-reading pagination")

            readings.extend(row for row in rows if isinstance(row, Mapping))
            if page >= expected_page_count:
                return readings
            if not rows:
                raise EemOnlineApiClientError("EEM returned an empty meter-reading page")
            page += 1

    async def _async_get_json(self, url: str) -> Any:
        """Fetch JSON with the current token, renewing it once if rejected."""
        if self._token is None:
            await self._async_login()

        try:
            return await self._async_fetch_json(url)
        except EemOnlineApiClientAuthenticationError:
            await self._async_login()
            return await self._async_fetch_json(url)

    async def _async_login(self) -> None:
        """Obtain an opaque EEM token."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.post(
                    f"{BASE_URL}/umbraco/surface/Auth/Auth",
                    json={"Username": self._username, "Password": self._password},
                ) as response:
                    if response.status in AUTH_FAILURE_STATUSES:
                        raise EemOnlineApiClientAuthenticationError("EEM rejected the credentials")
                    if response.status != 200:
                        raise EemOnlineApiClientCommunicationError(f"EEM login returned HTTP {response.status}")
                    token = (await response.text()).strip()
        except TimeoutError as err:
            raise EemOnlineApiClientCommunicationError("EEM login timed out") from err
        except aiohttp.ClientError as err:
            raise EemOnlineApiClientCommunicationError("EEM login request failed") from err

        if not token:
            raise EemOnlineApiClientError("EEM login returned an empty token")
        self._token = token

    async def _async_fetch_json(self, url: str) -> Any:
        """Fetch one authenticated JSON response."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(
                    URL(url, encoded=True), headers={"x-auth-token": self._token or ""}
                ) as response:
                    if response.status in AUTH_FAILURE_STATUSES:
                        self._token = None
                        raise EemOnlineApiClientAuthenticationError("EEM rejected the token")
                    if response.status == 204:
                        return None
                    if response.status != 200:
                        raise EemOnlineApiClientCommunicationError(f"EEM returned HTTP {response.status}")
                    payload = await response.json(content_type=None)
        except TimeoutError as err:
            raise EemOnlineApiClientCommunicationError("EEM data request timed out") from err
        except aiohttp.ClientError as err:
            raise EemOnlineApiClientCommunicationError("EEM data request failed") from err
        except ValueError as err:
            raise EemOnlineApiClientError("EEM returned invalid JSON") from err

        return payload
