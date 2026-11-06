"""Normalize the Ilsan CSV and persist its latest month, without date inference."""

import argparse
from collections import Counter
import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import sqlite3

DATASET_ID = "15114776"
SOURCE_URL = f"https://www.data.go.kr/data/{DATASET_ID}/fileData.do"
DAYS = tuple("월화수목금토일")
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "var/courses.sqlite3"
FIXTURE = ROOT / "data/fixtures/ilsan_2026-10.csv"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Course:
    code: str
    center: str
    month: str
    sport: str
    name: str
    days: tuple[str, ...]
    start: int
    end: int
    monthly_fee: int
    audience: str
    raw_start_date: str
    raw_end_date: str
    link: str
    raw: dict[str, str]


@dataclass(frozen=True)
class ParsedCSV:
    courses: tuple[Course, ...]
    row_count: int
    dropped: dict[str, int]
    encoding: str
    as_of_month: str


def parse_days(value: str) -> tuple[str, ...]:
    """Accept explicit comma-separated weekdays, returning calendar order."""
    tokens = {token.strip() for token in value.split(",")}
    if not tokens or not tokens <= set(DAYS):
        raise ValueError("요일 누락 또는 형식 오류")
    return tuple(day for day in DAYS if day in tokens)


def parse_clock(value: str, *, allow_midnight_end: bool = False) -> int:
    if allow_midnight_end and value == "24:00":
        return 1440
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise ValueError("시각은 HH:MM 형식이어야 합니다")
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def format_clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_time(value: str) -> tuple[int, int]:
    parts = value.strip().split("~")
    if len(parts) != 2:
        raise ValueError("시간 범위 오류")
    start = parse_clock(parts[0].strip())
    end = parse_clock(parts[1].strip(), allow_midnight_end=True)
    if start >= end:
        raise ValueError("종료 시각은 시작 시각보다 늦어야 합니다")
    return start, end


def parse_month(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return date.fromisoformat(value + "-01").strftime("%Y-%m")
    return date.fromisoformat(value).strftime("%Y-%m")


def parse_csv(data: bytes) -> ParsedCSV:
    """Count each invalid field independently; drop each invalid row once."""
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            decoded = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        # A UTF-8 file that happens to decode as CP949 must still have our header.
        reader = csv.DictReader(io.StringIO(decoded, newline=""))
        if reader.fieldnames and {"강좌번호", "시작월", "요일", "시작종료시간", "금액"} <= set(reader.fieldnames):
            break
    else:
        raise ValueError("지원하는 인코딩 또는 필수 CSV 헤더가 없습니다")

    courses: list[Course] = []
    dropped: Counter[str] = Counter()
    months: list[str] = []
    row_count = 0
    for row in reader:
        row_count += 1
        errors: list[str] = []
        original = {key: value or "" for key, value in row.items() if key is not None}
        raw = {key: value.strip() for key, value in original.items()}
        try:
            month = parse_month(raw.get("시작월", ""))
            months.append(month)
        except ValueError:
            errors.append("월")
        try:
            days = parse_days(raw.get("요일", ""))
        except ValueError:
            errors.append("요일")
        try:
            start, end = parse_time(raw.get("시작종료시간", ""))
        except ValueError:
            errors.append("시간")
        amount = raw.get("금액", "").replace(",", "")
        if not re.fullmatch(r"\d+", amount):
            errors.append("금액")
        if not raw.get("강좌번호"):
            errors.append("강좌번호")
        if errors:
            dropped.update(errors)
            continue
        courses.append(Course(
            code=raw["강좌번호"], center="일산스포츠센터", month=month,
            sport=raw.get("종목", ""), name=raw.get("강좌명", ""), days=days,
            start=start, end=end, monthly_fee=int(amount), audience=raw.get("강습반", ""),
            raw_start_date=raw.get("시작일", ""), raw_end_date=raw.get("종료일", ""),
            link=raw.get("링크", ""), raw=original,
        ))
    if not months:
        raise ValueError("유효한 시작월이 없습니다")
    logger.info("CSV rows=%d valid=%d dropped_by_reason=%s", row_count, len(courses), dict(dropped))
    return ParsedCSV(tuple(courses), row_count, dict(dropped), encoding, max(months))


def ingest(source: Path, database: Path = DEFAULT_DB) -> dict[str, str | int]:
    data = source.read_bytes()
    parsed = parse_csv(data)
    latest = [course for course in parsed.courses if course.month == parsed.as_of_month]
    if not latest:
        raise ValueError("최신 월의 유효 강좌가 없어 기존 DB를 유지합니다")
    meta: dict[str, str | int] = {
        "dataset_id": DATASET_ID, "source_file_name": source.name,
        "file_hash": hashlib.sha256(data).hexdigest(), "row_count": parsed.row_count,
        "valid_row_count": len(parsed.courses), "course_count": len(latest),
        "as_of_month": parsed.as_of_month,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dropped_by_reason": json.dumps(parsed.dropped, ensure_ascii=False),
    }
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS courses (code TEXT PRIMARY KEY, record TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("DELETE FROM courses")
        connection.executemany("INSERT INTO courses VALUES (?, ?)", [
            (course.code, json.dumps(asdict(course), ensure_ascii=False)) for course in latest
        ])
        connection.execute("DELETE FROM meta")
        connection.executemany("INSERT INTO meta VALUES (?, ?)", [
            (key, json.dumps(value, ensure_ascii=False)) for key, value in meta.items()
        ])
    return meta


def load_database(database: Path) -> tuple[tuple[Course, ...], dict[str, str | int]]:
    with sqlite3.connect(database) as connection:
        records = connection.execute("SELECT record FROM courses ORDER BY code").fetchall()
        meta = {key: json.loads(value) for key, value in connection.execute("SELECT key, value FROM meta")}
    courses = []
    for (record,) in records:
        fields = json.loads(record)
        fields["days"] = tuple(fields["days"])
        courses.append(Course(**fields))
    return tuple(courses), meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(ingest(args.source, args.db), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
