from dataclasses import replace

import pytest

from app.ingest import DAYS, FIXTURE, Course, parse_csv
from app.planner import Person, plan, search


def course(code: str, **kwargs: object) -> Course:
    base = Course(code, "일산스포츠센터", "2026-10", "농구", "테스트 강좌", ("화", "목"),
                  1080, 1130, 35000, "원문 강습반", "range", "raw date", "", {})
    return replace(base, **kwargs)


def person(**kwargs: object) -> Person:
    return replace(Person(frozenset(("화", "목")), 1080, 1140, max_monthly_fee=100000), **kwargs)


def test_real_demo_pair_fees_and_evidence() -> None:
    courses = parse_csv(FIXTURE.read_bytes()).courses
    result = plan(courses, person(), person(max_monthly_fee=70000))
    assert result.simultaneous
    pair = result.simultaneous[0]
    assert {pair.a.code, pair.b.code} == {"1029879", "21832"}
    assert pair.total_monthly_fee == 135000
    assert pair.days == ("화", "목")
    assert pair.overlap_minutes == 50
    assert pair.a.month == pair.b.month == "2026-10"
    assert pair.a.audience and pair.b.audience
    assert not result.suggestions


def test_adjacent_and_gap_limit() -> None:
    a = course("a", start=1020, end=1070)
    b = course("b")
    p = person(start=1000)
    result = plan((a, b), p, p)
    assert not result.simultaneous
    assert result.consecutive[0].gap_minutes == 10
    assert search((a, replace(b, start=1130, end=1180)), person(start=1000, end=1200), person(start=1000, end=1200)).consecutive
    assert not search((a, replace(b, start=1131, end=1180)), person(start=1000, end=1200), person(start=1000, end=1200)).consecutive


def test_simultaneous_sort_fee_then_longest_overlap() -> None:
    courses = (course("a"), course("b", start=1100), course("c", monthly_fee=10000))
    result = search(courses, person(), person())
    keys = [(pair.total_monthly_fee, -pair.overlap_minutes) for pair in result.simultaneous]
    assert keys == sorted(keys)


@pytest.mark.parametrize("kind", ["days", "budget", "time", "sport"])
def test_each_relaxation_is_exact_and_rerunnable(kind: str) -> None:
    courses = (course("a", sport="농구"), course("b", sport="TRX", monthly_fee=40000))
    a, b = person(sport="농구"), person(sport="TRX")
    if kind == "days":
        b = replace(b, days=frozenset(("화",)))
    elif kind == "budget":
        b = replace(b, max_monthly_fee=35000)
    elif kind == "time":
        b = replace(b, end=1100)
    else:
        b = replace(b, sport=None, excluded_sports=frozenset(("TRX",)))
    result = plan(courses, a, b)
    assert not result.simultaneous and not result.consecutive
    suggestion = next(s for s in result.suggestions if s.categories == frozenset((kind,)))
    assert suggestion.witness in search(courses, *suggestion.people).simultaneous
    assert suggestion.extra_monthly_fee == (5000 if kind == "budget" else 0)
    assert suggestion.added_days == (1 if kind == "days" else 0)
    assert suggestion.expanded_minutes == (30 if kind == "time" else 0)
    assert suggestion.sport_changes == (1 if kind == "sport" else 0)
    expected = {"days": "목요일", "budget": "5,000원", "time": "30분", "sport": "종목 제한"}[kind]
    assert any(expected in line for line in suggestion.changes)


def test_minimum_budget_and_time_from_actual_courses() -> None:
    courses = (course("a", sport="농구"), course("b", sport="TRX", monthly_fee=40000),
               course("c", sport="TRX", monthly_fee=90000))
    result = plan(courses, person(sport="농구"), person(sport="TRX", max_monthly_fee=35000))
    assert result.suggestions[0].extra_monthly_fee == 5000


def test_all_four_relaxation_types_rank_and_verify() -> None:
    courses = (
        course("a", sport="농구"),
        course("budget", sport="TRX", monthly_fee=40000),
        course("time", sport="TRX", end=1170),
        course("days", sport="TRX", days=("화", "목", "토")),
        course("sport", sport="요가"),
        course("more-time", sport="TRX", end=1200),
        course("more-days", sport="TRX", days=("화", "목", "토", "일")),
    )
    result = plan(courses, person(sport="농구"), person(sport="TRX", max_monthly_fee=35000))
    assert {next(iter(s.categories)) for s in result.suggestions} == {"days", "budget", "time", "sport"}
    assert [s.rank for s in result.suggestions] == sorted(s.rank for s in result.suggestions)
    for suggestion in result.suggestions:
        assert suggestion.witness in search(courses, *suggestion.people).simultaneous
        if suggestion.categories == frozenset(("time",)):
            assert suggestion.expanded_minutes == 30
        if suggestion.categories == frozenset(("days",)):
            assert suggestion.added_days == 1
            assert "토요일" in suggestion.changes[0]


def test_start_window_expansion_is_exact() -> None:
    result = plan((course("a"), course("b")), person(start=1110), person())
    suggestion = next(s for s in result.suggestions if s.categories == frozenset(("time",)))
    assert suggestion.expanded_minutes == 30
    assert "시작 시각을 30분 앞당기면" in suggestion.changes[0]
    assert search((course("a"), course("b")), *suggestion.people).simultaneous


def test_multiple_types_must_change_together() -> None:
    courses = (course("a"), course("b"))
    result = plan(courses, person(), person(days=frozenset(("화",)), end=1100, max_monthly_fee=30000))
    suggestion = result.suggestions[0]
    assert suggestion.categories == frozenset(("days", "time", "budget"))
    assert search(courses, *suggestion.people).simultaneous


def test_full_relaxation_cannot_invent_pair() -> None:
    result = plan((course("only"),), person(), person())
    assert result.fully_impossible
    assert not result.suggestions

    disjoint = plan((course("a", days=("월",)), course("b", days=("화",))), person(), person())
    assert disjoint.fully_impossible
    assert not disjoint.suggestions


def test_no_cross_month_center_or_disjoint_days_and_full_course_required() -> None:
    a = course("a")
    p = Person(frozenset(DAYS), 0, 1440)
    for b in (replace(a, code="b", month="2026-09"), replace(a, code="b", center="다른 센터"),
              replace(a, code="b", days=("월",))):
        assert not search((a, b), p, p).simultaneous
    assert not search((a, course("b")), person(days=frozenset(("화",))), person()).simultaneous


def test_touching_sessions_are_zero_gap_simultaneous() -> None:
    p = person(end=1200)
    result = search((course("a"), course("b", start=1130, end=1180)), p, p)
    assert result.simultaneous[0].overlap_minutes == 0


@pytest.mark.parametrize("kwargs", [{"start": 1140, "end": 1080}, {"max_monthly_fee": -1}, {"days": frozenset(("휴일",))}])
def test_invalid_constraints(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        person(**kwargs)
