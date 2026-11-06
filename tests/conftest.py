"""Keep tests independent of local credentials and the working directory."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATA_GO_KR_KEY", raising=False)
    monkeypatch.delenv("KSPO_BASE_URL", raising=False)
    monkeypatch.setenv("KSPO_DB_PATH", str(tmp_path / "var/courses.sqlite3"))
