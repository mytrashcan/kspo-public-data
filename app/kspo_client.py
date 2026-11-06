"""Minimal async client for caller-selected data.go.kr JSON APIs."""

from collections.abc import Mapping
from typing import TypeAlias
from urllib.parse import urlsplit

import httpx

from app.config import Settings, get_settings

JsonValue: TypeAlias = (
    dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None
)
QueryValue: TypeAlias = str | int | float | bool


class KspoApiError(RuntimeError):
    """Configuration, transport, or upstream API failure."""


def _check_result_code(payload: JsonValue) -> None:
    """Check common resultCode envelopes without inspecting data records."""
    if not isinstance(payload, dict):
        return

    for envelope in (payload, payload.get("response")):
        if not isinstance(envelope, dict):
            continue
        for header in (envelope, envelope.get("header")):
            if isinstance(header, dict) and "resultCode" in header:
                if str(header["resultCode"]).strip() not in {"0", "00", "0000"}:
                    # Do not echo upstream messages, which may contain credentials.
                    raise KspoApiError("KSPO API returned an unsuccessful resultCode.")


class KspoClient:
    """Fetch JSON using settings and an optional test transport."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings if settings is not None else get_settings()
        self._transport = transport

    async def get(
        self, dataset_path: str, params: Mapping[str, QueryValue] | None = None
    ) -> JsonValue:
        """GET a relative dataset path and return its parsed JSON."""
        if not self.settings.key_configured:
            raise KspoApiError("DATA_GO_KR_KEY is required for API calls.")

        base_url = self.settings.kspo_base_url.strip().rstrip("/")
        base = urlsplit(base_url)
        if (
            base.scheme not in {"http", "https"}
            or not base.netloc
            or base.username is not None
            or base.password is not None
            or base.query
            or base.fragment
        ):
            raise KspoApiError("KSPO_BASE_URL must be an HTTP(S) base URL.")

        path = urlsplit(dataset_path)
        if (
            path.scheme
            or path.netloc
            or path.query
            or path.fragment
            or not path.path.strip("/")
        ):
            raise KspoApiError("dataset_path must be a path without a query or host.")

        # TODO: Look up real dataset IDs, endpoint paths, and parameters on data.go.kr.
        url = f"{base_url}/{path.path.lstrip('/')}"
        query = dict(params or {})
        query["serviceKey"] = self.settings.data_go_kr_key.get_secret_value().strip()

        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=10.0, follow_redirects=False
            ) as client:
                response = await client.get(url, params=query)
        except httpx.RequestError:
            # httpx exceptions may include the request URL and its serviceKey.
            raise KspoApiError("KSPO API request failed.") from None

        if response.status_code != 200:
            raise KspoApiError(f"KSPO API returned HTTP {response.status_code}.")

        try:
            payload: JsonValue = response.json()
        except ValueError:
            raise KspoApiError("KSPO API returned invalid JSON.") from None

        _check_result_code(payload)
        return payload
