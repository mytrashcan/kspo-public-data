import csv
import hashlib
import io
from pathlib import Path

import pytest

from app.ingest import FIXTURE, ingest, load_database, parse_csv, parse_days, parse_time


def csv_bytes(rows: list[dict[str, str]], encoding: str = "cp949") -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode(encoding)


@pytest.mark.parametrize("encoding", ["cp949", "utf-8-sig", "utf-8"])
def test_encoding_and_dates(encoding: str) -> None:
    row = parse_csv(FIXTURE.read_bytes()).courses[0].raw.copy()
    row["시작일"] = "2000-01-01~9999-12-31"
    row["종료일"] = "2000-01-01"
    parsed = parse_csv(csv_bytes([row], encoding))
    course = parsed.courses[0]
    assert course.month == "2026-10"
    assert course.raw_start_date == row["시작일"]
    assert course.raw_end_date == row["종료일"]
    assert course.audience == row["강습반"]


def test_drops_count_each_reason(caplog: pytest.LogCaptureFixture) -> None:
    row = parse_csv(FIXTURE.read_bytes()).courses[0].raw.copy()
    rows = []
    for field in ("요일", "시작종료시간", "시작월", "금액"):
        rows.append({**row, field: ""})
    with caplog.at_level("INFO"):
        parsed = parse_csv(csv_bytes([row, *rows]))
    assert len(parsed.courses) == 1
    assert parsed.row_count == 5
    assert parsed.dropped == {"요일": 1, "시간": 1, "월": 1, "금액": 1}
    assert "dropped_by_reason" in caplog.text


def test_fixture_and_sqlite_latest_provenance(tmp_path: Path) -> None:
    parsed = parse_csv(FIXTURE.read_bytes())
    assert parsed.row_count == 157
    assert len(parsed.courses) == 155
    assert parsed.dropped == {"시간": 2}
    old = {**parsed.courses[0].raw, "시작월": "2020-01-01"}
    source = tmp_path / "mixed.csv"
    source.write_bytes(csv_bytes([old, parsed.courses[1].raw]))
    db = tmp_path / "var/test.sqlite3"
    meta = ingest(source, db)
    courses, loaded_meta = load_database(db)
    assert meta == loaded_meta
    assert len(courses) == 1
    assert courses[0].month == "2026-10"
    assert meta["row_count"] == 2
    assert meta["course_count"] == 1
    assert meta["file_hash"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert meta["dataset_id"] == "15114776"
    assert meta["generated_at"]


def test_latest_invalid_month_does_not_silently_fall_back(tmp_path: Path) -> None:
    row = parse_csv(FIXTURE.read_bytes()).courses[0].raw
    source = tmp_path / "bad.csv"
    source.write_bytes(csv_bytes([row, {**row, "시작월": "2026-11-01", "금액": ""}]))
    with pytest.raises(ValueError, match="최신 월"):
        ingest(source, tmp_path / "db")


def test_days_order() -> None:
    assert parse_days("금,월,화,수,목,월") == tuple("월화수목금")


@pytest.mark.parametrize("value", ["", "월~금", "월,공휴일", "월,"])
def test_invalid_days(value: str) -> None:
    with pytest.raises(ValueError):
        parse_days(value)


@pytest.mark.parametrize("value", ["", "18시", "25:00~26:00", "18:60~19:00", "19:00~18:00", "14:00~14:00", "18:00-19:00"])
def test_invalid_time(value: str) -> None:
    with pytest.raises(ValueError):
        parse_time(value)


def test_time_minutes() -> None:
    assert parse_time("18:00~18:50") == (1080, 1130)
