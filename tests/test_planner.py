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
    assert set(pair.codes) == {"1029879", "21832"}
    assert pair.total_monthly_fee == 135000
    assert pair.days == ("화", "목")
    assert pair.overlap_minutes == 50
    assert {course.month for course in pair.courses} == {"2026-10"}
    assert all(course.audience for course in pair.courses)
    assert not result.suggestions


WEEKDAYS = frozenset(("월", "화", "수", "목", "금"))


def test_real_three_person_group_ends_together() -> None:
    """검도 + 배드민턴 + 스쿼시: 화·목 21:50에 셋이 같이 끝나고, 합계 197,000원."""
    courses = parse_csv(FIXTURE.read_bytes()).courses
    people = (Person(WEEKDAYS, 1260, 1320, sport="검도"),
              Person(WEEKDAYS, 1140, 1320, sport="배드민턴"),
              Person(frozenset(("화", "목", "토", "일")), 1260, 1320, sport="스쿼시"))
    result = plan(courses, *people)
    group = result.simultaneous[0]
    assert group.codes == ("1022624", "21365", "1016477")
    assert [course.monthly_fee for course in group.courses] == [70000, 65000, 62000]
    assert group.total_monthly_fee == 197000
    assert group.days == ("화", "목")
    assert {course.end for course in group.courses} == {1310}
    assert group.end == 1310 and group.first_start == 1140
    assert group.overlap_minutes == 50
    assert not result.suggestions


def test_every_person_needs_a_different_course_on_a_shared_day() -> None:
    wide = person(start=1000, end=1200)
    two = (course("a"), course("b"))
    assert search(two, wide, wide).simultaneous
    # 강좌 두 개로는 세 사람이 서로 다른 수업을 들을 수 없다
    assert not search(two, wide, wide, wide).simultaneous
    three = two + (course("c"),)
    assert len(search(three, wide, wide, wide).simultaneous) == 6
    # 셋째 수업이 마치는 시각이 다르거나, 셋이 겹치는 요일이 없으면 조합이 아니다
    assert not search(two + (course("c", end=1180),), wide, wide, wide).simultaneous
    everyday = replace(wide, days=frozenset(DAYS))
    split = (course("a", days=("화", "수")), course("b", days=("수", "목")), course("c", days=("목", "화")))
    assert not search(split, everyday, everyday, everyday).simultaneous
    group = search(two + (course("c", start=1110),), wide, wide, wide).simultaneous[0]
    assert group.overlap_minutes == 20


def test_group_size_is_two_to_four() -> None:
    with pytest.raises(ValueError):
        search((course("a"),), person())
    with pytest.raises(ValueError):
        search((course("a"),), *(person(),) * 5)


def test_four_person_relaxation_is_per_person_and_rerun() -> None:
    courses = tuple(course(code, sport=sport, monthly_fee=fee) for code, sport, fee in
                    (("a", "농구", 35000), ("b", "TRX", 40000), ("c", "요가", 30000), ("d", "검도", 50000)))
    people = (person(sport="농구"), person(sport="TRX", max_monthly_fee=35000),
              person(sport="요가", days=frozenset(("화",))), person(sport="검도"))
    result = plan(courses, *people)
    assert not result.simultaneous and result.suggestions
    combined = result.suggestions[0]
    assert combined.categories == frozenset(("budget", "days"))
    assert combined.changes == ("B: 예산을 월 5,000원 늘리면 성립 (35,000원 → 40,000원)",
                                "C: 목요일을 추가로 허용하면 성립")
    assert combined.people[0] == people[0] and combined.people[3] == people[3]
    assert combined.witness in search(courses, *combined.people).simultaneous


def test_end_times_must_match() -> None:
    """두 사람이 함께 나오려면 마치는 시각이 같아야 한다."""
    a = course("a")
    wide = person(start=1000, end=1200)
    assert search((a, course("b")), wide, wide).simultaneous
    # 마치는 시각이 다르면 조합이 아니다 (한 사람이 먼저 끝나 기다리게 된다)
    assert not search((a, replace(course("b"), end=1180)), wide, wide).simultaneous
    assert not search((a, replace(course("b"), start=1130, end=1180)), wide, wide).simultaneous
    # 시작이 달라도 마치는 시각이 같으면 겹치는 시간만큼은 함께 있다
    later = search((a, replace(course("b"), start=1100)), person(), person())
    assert later.simultaneous[0].overlap_minutes == 30


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
    assert not result.simultaneous
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


def test_relaxations_are_ranked_and_each_witness_verified() -> None:
    courses = (
        course("a", sport="농구"),
        course("budget", sport="TRX", monthly_fee=40000),
        course("days", sport="TRX", days=("화", "목", "토")),
        course("sport", sport="요가"),
    )
    result = plan(courses, person(sport="농구"),
                  person(sport="TRX", max_monthly_fee=35000, end=1100, days=frozenset(("화",))))
    assert result.suggestions
    assert [s.rank for s in result.suggestions] == sorted(s.rank for s in result.suggestions)
    for suggestion in result.suggestions:
        assert suggestion.witness in search(courses, *suggestion.people).simultaneous
    touched = set().union(*(s.categories for s in result.suggestions))
    assert {"days", "time"} <= touched


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


def test_sessions_that_only_touch_are_not_a_pair() -> None:
    """앞 수업이 끝난 뒤 다음 수업이 시작하는 '이어서' 조합은 함께 운동이 아니므로 제외한다."""
    p = person(end=1200)
    assert not search((course("a"), course("b", start=1130, end=1180)), p, p).simultaneous


@pytest.mark.parametrize("kwargs", [{"start": 1140, "end": 1080}, {"max_monthly_fee": -1}, {"days": frozenset(("휴일",))}])
def test_invalid_constraints(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        person(**kwargs)
