"""Gate probe: can the 일산스포츠센터 강좌정보 CSV support a two-person 동행 조합 engine?

Measures, on the newest 강좌 month only:
  - usable course count
  - same-slot pairs (two different 종목 at the same weekday+time)  -> "같이 가서 각자 운동"
  - same-day adjacent pairs                                        -> "같은 날 연달아"
  - minimal-change candidates when a requested (day, budget, time) fails

Run: /usr/local/bin/python3 gate_probe.py <csv> [target_month]
"""
from __future__ import annotations

import collections
import csv
import io
import re
import sys
from dataclasses import dataclass

DAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]


@dataclass(frozen=True)
class Course:
    no: str
    month: str
    sport: str
    name: str
    days: tuple[str, ...]
    start_min: int
    end_min: int
    fee: int
    target: str
    raw_start: str
    raw_end: str


def parse_days(value: str) -> tuple[str, ...]:
    out = []
    for token in re.split(r"[,/·\s]+", value.strip()):
        token = token.strip()
        if token in DAY_ORDER and token not in out:
            out.append(token)
    return tuple(sorted(out, key=DAY_ORDER.index))


def parse_time_range(value: str) -> tuple[int, int] | None:
    m = re.match(r"\s*(\d{1,2}):(\d{2})\s*[~\-]\s*(\d{1,2}):(\d{2})", value)
    if not m:
        return None
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    start, end = h1 * 60 + m1, h2 * 60 + m2
    if not (0 <= start < end <= 24 * 60):
        return None
    return start, end


def load(path: str) -> list[Course]:
    raw = open(path, "rb").read()
    for enc in ("cp949", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.DictReader(io.StringIO(text)))
    out: list[Course] = []
    for row in rows:
        days = parse_days(row.get("요일", ""))
        span = parse_time_range(row.get("시작종료시간", ""))
        # Known quirk: '시작일' holds a range string, '종료일' holds the real start date.
        month = (row.get("시작월") or "").strip()[:7]
        if not month:
            m = re.match(r"\s*(\d{4}-\d{2}-\d{2})", row.get("시작일", ""))
            month = m.group(1)[:7] if m else ""
        try:
            fee = int(re.sub(r"[^\d]", "", row.get("금액", "")) or 0)
        except ValueError:
            fee = 0
        if not (days and span and month and fee):
            continue
        out.append(
            Course(
                no=(row.get("강좌번호") or "").strip(),
                month=month,
                sport=(row.get("종목") or "").strip(),
                name=(row.get("강좌명") or "").strip(),
                days=days,
                start_min=span[0],
                end_min=span[1],
                fee=fee,
                target=(row.get("강습반") or "").strip(),
                raw_start=(row.get("시작일") or "").strip(),
                raw_end=(row.get("종료일") or "").strip(),
            )
        )
    return out


def overlaps(a: Course, b: Course) -> tuple[bool, bool]:
    """Return (same weekday, time overlap)."""
    same_day = bool(set(a.days) & set(b.days))
    overlap = same_day and max(a.start_min, b.start_min) < min(a.end_min, b.end_min)
    return same_day, overlap


def main() -> None:
    path = sys.argv[1]
    courses = load(path)
    months = collections.Counter(c.month for c in courses)
    target = sys.argv[2] if len(sys.argv) > 2 else max(months)
    current = [c for c in courses if c.month == target]

    print(f"file rows parsed     : {len(courses)}")
    print(f"months               : {len(months)} (min {min(months)}, max {max(months)})")
    print(f"target month         : {target}")
    print(f"usable courses       : {len(current)}")
    print(f"distinct sports      : {len({c.sport for c in current})}")
    print(f"fee range            : {min(c.fee for c in current)} ~ {max(c.fee for c in current)}")

    slot_pairs = 0
    same_day_pairs = 0
    examples = []
    for i, a in enumerate(current):
        for b in current[i + 1:]:
            if a.sport == b.sport:
                continue
            same_day, overlap = overlaps(a, b)
            if overlap:
                slot_pairs += 1
                if len(examples) < 5:
                    examples.append((a, b))
            elif same_day:
                gap = max(a.start_min, b.start_min) - min(a.end_min, b.end_min)
                if abs(gap) <= 60:
                    same_day_pairs += 1

    print(f"same-slot pairs      : {slot_pairs} (동시에 각자 운동)")
    print(f"adjacent pairs       : {same_day_pairs} (같은 날 60분 이내 간격)")
    for a, b in examples:
        print(
            f"  - {a.days}/{a.start_min//60:02d}:{a.start_min%60:02d}"
            f" {a.sport}({a.fee:,}) + {b.sport}({b.fee:,})"
        )

    # minimal-change probe: 요청 조건이 성립하지 않을 때 무엇을 얼마나 바꾸면 되는가
    request_day, request_budget = "화", 150_000
    day_ok = [c for c in current if request_day in c.days]
    fits = [c for c in day_ok if c.fee*2 <= request_budget]
    print(f"\nrequest: {request_day}요일 / 두 명 합계 {request_budget:,}원 이하")
    print(f"  candidates on {request_day}: {len(day_ok)}, within budget: {len(fits)}")
    if not fits and day_ok:
        cheapest = sorted(day_ok, key=lambda c: c.fee)[:2]
        needed = sum(c.fee for c in cheapest)
        print(f"  minimal change: 예산 {needed:,}원까지 +{needed-request_budget:,}원")
    elif fits:
        pair = sorted(fits, key=lambda c: c.fee)[:2]
        print(f"  minimal fit: {pair[0].sport}+{pair[1].sport} = {sum(c.fee for c in pair):,}원")

    # 종목 커버리지 상위
    print("\ntop sports:", collections.Counter(c.sport for c in current).most_common(6))
    print("target labels:", collections.Counter(c.target for c in current).most_common(6))


if __name__ == "__main__":
    main()
