"""Synthetic transport inputs; these are not real dataset API responses."""

import asyncio

import httpx
import pytest

from app.config import Settings
from app.kspo_client import JsonValue, KspoApiError, KspoClient


@pytest.fixture
def settings() -> Settings:
    return Settings(
        data_go_kr_key="test-only-key+/=", kspo_base_url="https://example.invalid/base/"
    )


@pytest.mark.parametrize("dataset_path", ["unit-test", "/unit-test"])
def test_get_success(settings: Settings, dataset_path: str) -> None:
    payload = {"response": {"header": {"resultCode": "00"}}}
    params = {"unit_test_param": "한글", "serviceKey": "must-not-override"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url.copy_with(query=None)) == "https://example.invalid/base/unit-test"
        assert request.url.params["serviceKey"] == "test-only-key+/="
        assert request.url.params["unit_test_param"] == "한글"
        assert len(request.url.params.get_list("serviceKey")) == 1
        return httpx.Response(200, json=payload)

    client = KspoClient(settings, transport=httpx.MockTransport(handler))
    assert asyncio.run(client.get(dataset_path, params)) == payload
    assert params["serviceKey"] == "must-not-override"


@pytest.mark.parametrize("status", [201, 302, 403, 500])
def test_http_error(settings: Settings, status: int) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    client = KspoClient(settings, transport=transport)

    with pytest.raises(KspoApiError, match=f"HTTP {status}"):
        asyncio.run(client.get("unit-test"))


@pytest.mark.parametrize(
    "payload",
    [
        {"resultCode": "99"},
        {"header": {"resultCode": "99"}},
        {"response": {"resultCode": "99"}},
        {"response": {"header": {"resultCode": "99"}}},
    ],
)
def test_result_code_error(settings: Settings, payload: JsonValue) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = KspoClient(settings, transport=transport)

    with pytest.raises(KspoApiError, match="resultCode"):
        asyncio.run(client.get("unit-test"))


@pytest.mark.parametrize("code", [0, "0", "00", "0000"])
def test_success_codes(settings: Settings, code: str | int) -> None:
    payload = {"resultCode": code}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client = KspoClient(settings, transport=transport)

    assert asyncio.run(client.get("unit-test")) == payload


def test_missing_key_raises_before_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Missing credentials must prevent a request.")

    # Constructing settings and the client is safe without a key or URL.
    client = KspoClient(transport=httpx.MockTransport(handler))
    with pytest.raises(KspoApiError, match="DATA_GO_KR_KEY"):
        asyncio.run(client.get("unit-test"))


def test_missing_base_url_raises_before_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Missing base URL must prevent a request.")

    client = KspoClient(Settings(data_go_kr_key="test-only"), transport=httpx.MockTransport(handler))
    with pytest.raises(KspoApiError, match="KSPO_BASE_URL"):
        asyncio.run(client.get("unit-test"))


def test_invalid_json(settings: Settings) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text="not JSON"))
    client = KspoClient(settings, transport=transport)

    with pytest.raises(KspoApiError, match="invalid JSON"):
        asyncio.run(client.get("unit-test"))


def test_transport_error_does_not_expose_key(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(str(request.url), request=request)

    client = KspoClient(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(KspoApiError, match="request failed") as error:
        asyncio.run(client.get("unit-test"))
    assert "serviceKey" not in str(error.value)
    assert settings.data_go_kr_key.get_secret_value() not in str(error.value)
