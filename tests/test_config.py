from pathlib import Path

import pytest

from app.config import get_settings


def test_settings_allow_missing_key() -> None:
    settings = get_settings()

    assert settings.key_configured is False
    assert settings.kspo_base_url == ""


def test_settings_read_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DATA_GO_KR_KEY=dotenv-test-only\nKSPO_BASE_URL=https://example.invalid/base\n",
        encoding="utf-8",
    )

    settings = get_settings()

    assert settings.data_go_kr_key.get_secret_value() == "dotenv-test-only"
    assert settings.kspo_base_url == "https://example.invalid/base"
    assert settings.key_configured is True
    assert "dotenv-test-only" not in repr(settings)


def test_environment_overrides_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DATA_GO_KR_KEY=dotenv-test-only\nKSPO_BASE_URL=https://example.invalid/dotenv\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATA_GO_KR_KEY", "env-test-only")
    monkeypatch.setenv("KSPO_BASE_URL", "https://example.invalid/environment")

    settings = get_settings()

    assert settings.data_go_kr_key.get_secret_value() == "env-test-only"
    assert settings.kspo_base_url == "https://example.invalid/environment"
