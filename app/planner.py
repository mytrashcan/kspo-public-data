"""Find evidenced groups (2–4 people) and verify the smallest changes within each change type."""

from collections import defaultdict
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


MIN_PEOPLE, MAX_PEOPLE = 2, 4
LABELS = ("A", "B", "C", "D")


@dataclass(frozen=True)
class Combination:
    """One course per person, in person order; all on common days and ending together."""
    courses: tuple[Course, ...]
    days: tuple[str, ...]
    overlap_minutes: int

    @property
    def total_monthly_fee(self) -> int:
        return sum(course.monthly_fee for course in self.courses)

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(course.code for course in self.courses)

    @property
    def first_start(self) -> int:
        """When the earliest class starts: the group arrives together by then."""
        return min(course.start for course in self.courses)

    @property
    def end(self) -> int:
        return self.courses[0].end


@dataclass(frozen=True)
class Relaxation:
    categories: frozenset[str]
    changes: tuple[str, ...]
    extra_monthly_fee: int
    added_days: int
    expanded_minutes: int
    sport_changes: int
    people: tuple[Person, ...]
    witness: Combination

    @property
    def rank(self) -> tuple[int, ...]:
        return (len(self.changes), self.extra_monthly_fee, self.added_days,
                self.expanded_minutes, self.sport_changes, self.witness.total_monthly_fee)


@dataclass(frozen=True)
class Plan:
    simultaneous: tuple[Combination, ...]
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


def _groups(candidates: list[list[Course]]) -> list[Combination]:
    """Every assignment of distinct courses, one per person, that shares a day and an end time."""
    buckets: list[dict[tuple[str, str, int], list[Course]]] = []
    for eligible in candidates:
        bucket: dict[tuple[str, str, int], list[Course]] = defaultdict(list)
        for course in eligible:
            # 함께 나가려면 마치는 시각이 같아야 한다: 같은 센터·같은 달·같은 종료 시각끼리만 본다.
            bucket[(course.center, course.month, course.end)].append(course)
        buckets.append(bucket)
    found: list[Combination] = []

    def extend(key: tuple[str, str, int], index: int, chosen: tuple[Course, ...], days: frozenset[str]) -> None:
        if index == len(buckets):
            common = tuple(day for day in DAYS if day in days)
            found.append(Combination(chosen, common, key[2] - max(course.start for course in chosen)))
            return
        for course in buckets[index].get(key, ()):
            shared = days & set(course.days)
            if shared and all(course.code != other.code for other in chosen):
                extend(key, index + 1, chosen + (course,), shared)

    for key in set(buckets[0]).intersection(*buckets[1:]):
        extend(key, 0, (), frozenset(DAYS))
    return found


def _check_size(people: tuple[Person, ...]) -> None:
    if not MIN_PEOPLE <= len(people) <= MAX_PEOPLE:
        raise ValueError(f"{MIN_PEOPLE}명에서 {MAX_PEOPLE}명까지 함께 찾을 수 있어요")


def search(courses: tuple[Course, ...], *people: Person) -> Plan:
    """Require every listed class day and its full session to fit each person."""
    _check_size(people)
    found = _groups([[course for course in courses if _eligible(course, person)] for person in people])
    found.sort(key=lambda group: (group.total_monthly_fee, -group.overlap_minutes, group.codes))
    return Plan(tuple(found))


def _required_changes(group: Combination, people: tuple[Person, ...]) -> Relaxation:
    """Derive exact boundary changes per person from a real group, never hypothetical prices."""
    updated: list[Person] = []
    changes: list[str] = []
    categories: set[str] = set()
    extra_fee = added_days = expanded_minutes = sport_changes = 0
    for label, course, person in zip(LABELS, group.courses, people):
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
                      expanded_minutes, sport_changes, tuple(updated), group)


def _within_type_rank(change: Relaxation) -> tuple[int, ...]:
    if len(change.categories) == 1:
        category = next(iter(change.categories))
        cost = {"days": change.added_days, "budget": change.extra_monthly_fee,
                "time": change.expanded_minutes, "sport": change.sport_changes}[category]
        return (cost, *change.rank)
    return change.rank


def plan(courses: tuple[Course, ...], *people: Person) -> Plan:
    result = search(courses, *people)
    if result.simultaneous:
        return result
    unrestricted = Person(frozenset(DAYS), 0, 1440)
    full = search(courses, *(unrestricted,) * len(people))
    if not full.simultaneous:
        return replace(result, fully_impossible=True)

    # One minimum per individual type; if none works alone, one combined change.
    best: dict[str, Relaxation] = {}
    for group in full.simultaneous:
        candidate = _required_changes(group, people)
        key = next(iter(candidate.categories)) if len(candidate.categories) == 1 else "combined"
        if key not in best or _within_type_rank(candidate) < _within_type_rank(best[key]):
            best[key] = candidate
    single = [value for key, value in best.items() if key != "combined"]
    candidates = single or [best["combined"]]
    verified = []
    for candidate in candidates:
        # 제안은 바꾼 조건으로 다시 검색해서 그 조합이 실제로 나올 때만 보여 준다.
        rerun = search(courses, *candidate.people)
        if candidate.witness in rerun.simultaneous:
            verified.append(candidate)
    return replace(result, suggestions=tuple(sorted(verified, key=lambda change: change.rank)))
