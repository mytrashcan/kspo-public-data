"""Find evidenced pairs and verify the smallest changes within each change type."""

from dataclasses import dataclass, replace

from app.ingest import Course, DAYS, format_clock


@dataclass(frozen=True)
class Person:
    days: frozenset[str]
    start: int
    end: int
    sport: str | None = None
    excluded_sports: frozenset[str] = frozenset()
    max_monthly_fee: int | None = None

    def __post_init__(self) -> None:
        if not self.days <= set(DAYS):
            raise ValueError("허용하지 않는 요일입니다")
        if not 0 <= self.start < self.end <= 1440:
            raise ValueError("시간 범위를 확인해 주세요")
        if self.max_monthly_fee is not None and self.max_monthly_fee < 0:
            raise ValueError("예산은 0원 이상이어야 합니다")


@dataclass(frozen=True)
class Combination:
    a: Course
    b: Course
    days: tuple[str, ...]
    overlap_minutes: int
    gap_minutes: int

    @property
    def total_monthly_fee(self) -> int:
        return self.a.monthly_fee + self.b.monthly_fee

    @property
    def simultaneous(self) -> bool:
        return self.gap_minutes == 0


@dataclass(frozen=True)
class Relaxation:
    categories: frozenset[str]
    changes: tuple[str, ...]
    extra_monthly_fee: int
    added_days: int
    expanded_minutes: int
    sport_changes: int
    people: tuple[Person, Person]
    witness: Combination

    @property
    def rank(self) -> tuple[int, ...]:
        return (len(self.changes), self.extra_monthly_fee, self.added_days,
                self.expanded_minutes, self.sport_changes, self.witness.total_monthly_fee)


@dataclass(frozen=True)
class Plan:
    simultaneous: tuple[Combination, ...]
    consecutive: tuple[Combination, ...]
    suggestions: tuple[Relaxation, ...] = ()
    fully_impossible: bool = False


def _sport_matches(course: Course, person: Person) -> bool:
    return (not person.sport or course.sport == person.sport) and course.sport not in person.excluded_sports


def _eligible(course: Course, person: Person) -> bool:
    return (
        set(course.days) <= person.days
        and course.start >= person.start and course.end <= person.end
        and _sport_matches(course, person)
        and (person.max_monthly_fee is None or course.monthly_fee <= person.max_monthly_fee)
    )


def _pair(a: Course, b: Course) -> Combination | None:
    if a.code == b.code or a.center != b.center or a.month != b.month:
        return None
    days = tuple(day for day in DAYS if day in a.days and day in b.days)
    if not days:
        return None
    overlap = min(a.end, b.end) - max(a.start, b.start)
    if overlap < -60:
        return None
    return Combination(a, b, days, max(0, overlap), max(0, -overlap))


def search(courses: tuple[Course, ...], a: Person, b: Person) -> Plan:
    """Require every listed class day and its full session to fit each person."""
    simultaneous: list[Combination] = []
    consecutive: list[Combination] = []
    eligible_a = [course for course in courses if _eligible(course, a)]
    eligible_b = [course for course in courses if _eligible(course, b)]
    for course_a in eligible_a:
        for course_b in eligible_b:
            pair = _pair(course_a, course_b)
            if pair is not None:
                (simultaneous if pair.simultaneous else consecutive).append(pair)
    simultaneous.sort(key=lambda pair: (pair.total_monthly_fee, -pair.overlap_minutes, pair.a.code, pair.b.code))
    consecutive.sort(key=lambda pair: (pair.total_monthly_fee, pair.gap_minutes, pair.a.code, pair.b.code))
    return Plan(tuple(simultaneous), tuple(consecutive))


def _required_changes(pair: Combination, people: tuple[Person, Person]) -> Relaxation:
    """Derive exact boundary changes from a real pair, never hypothetical prices."""
    updated: list[Person] = []
    changes: list[str] = []
    categories: set[str] = set()
    extra_fee = added_days = expanded_minutes = sport_changes = 0
    for label, course, person in zip(("A", "B"), (pair.a, pair.b), people):
        missing = tuple(day for day in DAYS if day in course.days and day not in person.days)
        if missing:
            categories.add("days")
            added_days += len(missing)
            changes.append(f"{label}: {'·'.join(day + '요일' for day in missing)}을 추가로 허용하면 성립")
        extra = max(0, course.monthly_fee - person.max_monthly_fee) if person.max_monthly_fee is not None else 0
        if extra:
            categories.add("budget")
            extra_fee += extra
            changes.append(f"{label}: 예산을 월 {extra:,}원 늘리면 성립 ({person.max_monthly_fee:,}원 → {course.monthly_fee:,}원)")
        earlier, later = max(0, person.start - course.start), max(0, course.end - person.end)
        if earlier:
            categories.add("time")
            expanded_minutes += earlier
            changes.append(f"{label}: 시작 시각을 {earlier}분 앞당기면 성립 ({format_clock(person.start)} → {format_clock(course.start)})")
        if later:
            categories.add("time")
            expanded_minutes += later
            changes.append(f"{label}: 종료 시각을 {later}분 늦추면 성립 ({format_clock(person.end)} → {format_clock(course.end)})")
        sport_change = not _sport_matches(course, person)
        if sport_change:
            categories.add("sport")
            sport_changes += 1
            changes.append(f"{label}: 종목 제한을 풀면 성립 (선호·제외 해제)")
        updated.append(replace(
            person, days=person.days | frozenset(missing),
            start=min(person.start, course.start), end=max(person.end, course.end),
            max_monthly_fee=course.monthly_fee if extra else person.max_monthly_fee,
            sport=None if sport_change else person.sport,
            excluded_sports=frozenset() if sport_change else person.excluded_sports,
        ))
    return Relaxation(frozenset(categories), tuple(changes), extra_fee, added_days,
                      expanded_minutes, sport_changes, (updated[0], updated[1]), pair)


def _within_type_rank(change: Relaxation) -> tuple[int, ...]:
    if len(change.categories) == 1:
        category = next(iter(change.categories))
        cost = {"days": change.added_days, "budget": change.extra_monthly_fee,
                "time": change.expanded_minutes, "sport": change.sport_changes}[category]
        return (cost, *change.rank)
    return change.rank


def plan(courses: tuple[Course, ...], a: Person, b: Person) -> Plan:
    result = search(courses, a, b)
    if result.simultaneous or result.consecutive:
        return result
    unrestricted = Person(frozenset(DAYS), 0, 1440)
    full = search(courses, unrestricted, unrestricted)
    if not full.simultaneous and not full.consecutive:
        return replace(result, fully_impossible=True)

    # One minimum per individual type; if none works alone, one combined change.
    best: dict[str, Relaxation] = {}
    for pair in (*full.simultaneous, *full.consecutive):
        candidate = _required_changes(pair, (a, b))
        key = next(iter(candidate.categories)) if len(candidate.categories) == 1 else "combined"
        if key not in best or _within_type_rank(candidate) < _within_type_rank(best[key]):
            best[key] = candidate
    single = [value for key, value in best.items() if key != "combined"]
    candidates = single or [best["combined"]]
    verified = []
    for candidate in candidates:
        rerun = search(courses, *candidate.people)
        if candidate.witness in (*rerun.simultaneous, *rerun.consecutive):
            verified.append(candidate)
    return replace(result, suggestions=tuple(sorted(verified, key=lambda change: change.rank)))
