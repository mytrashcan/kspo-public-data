import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize("key, configured", [("", False), ("   ", False), ("test-only", True)])
def test_health(monkeypatch: pytest.MonkeyPatch, key: str, configured: bool) -> None:
    monkeypatch.setenv("DATA_GO_KR_KEY", key)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data_go_kr_key_configured": configured}
    assert "test-only" not in response.text


def test_root_reports_scaffold() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "기획 단계 / 스캐폴드"
