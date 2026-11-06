"""Server-rendered shared exercise planner; no external requests at runtime."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import os
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException

from app.config import Settings, get_settings
from app.ingest import DEFAULT_DB, DAYS, FIXTURE, ROOT, SOURCE_URL, format_clock, ingest, load_database, parse_clock
from app.planner import MAX_PEOPLE, MIN_PEOPLE, Person, plan, search

DISCLAIMER = "정원은 잔여석이 아니며 수강 신청 가능 여부를 보장하지 않습니다."
DEMO = (
    Person(frozenset(("화", "목")), 1080, 1140, max_monthly_fee=100000),
    Person(frozenset(("화", "목")), 1080, 1140, max_monthly_fee=70000),
)
# Three people, verified against the 2026-10 fixture: 검도 + 배드민턴 + 스쿼시, all ending 21:50 on 화·목.
WEEKDAYS = frozenset(("월", "화", "수", "목", "금"))
DEMO_GROUP = (
    Person(WEEKDAYS, 1260, 1320, sport="검도"),
    Person(WEEKDAYS, 1140, 1320, sport="배드민턴"),
    Person(frozenset(("화", "목", "토", "일")), 1260, 1320, sport="스쿼시"),
)
templates = Jinja2Templates(directory=ROOT / "app/templates")
templates.env.filters["clock"] = format_clock
templates.env.filters["money"] = lambda value: f"{value:,}"

# Query keys per person, in order. a_/b_ are the original two and must not change.
PREFIXES = ("a", "b", "c", "d")


def plan_url(people: tuple[Person, ...]) -> str:
    params: list[tuple[str, str]] = []
    for prefix, person in zip(PREFIXES, people):
        params.extend((f"{prefix}_days", day) for day in DAYS if day in person.days)
        params.extend(((f"{prefix}_start", format_clock(person.start)),
                       (f"{prefix}_end", format_clock(person.end))))
        if person.max_monthly_fee is not None:
            params.append((f"{prefix}_budget", str(person.max_monthly_fee)))
        if person.sport:
            params.append((f"{prefix}_sport", person.sport))
        params.extend((f"{prefix}_exclude", sport) for sport in sorted(person.excluded_sports))
    return "/plan?" + urlencode(params)


templates.env.globals["plan_url"] = plan_url


def roster(count: int) -> list[dict[str, str]]:
    """How people are called on screen. Two people are 나 and 짝; from three on, "짝" no longer
    fits, so companions are counted off the way a group does at the gym: 2번, 3번, 4번."""
    if count == 2:
        names = (("나", "나", "나는", "내"), ("짝", "짝", "짝은", "짝의"))
    else:
        names = (("나", "나", "나는", "내"),) + tuple(
            (str(number), f"{number}번", f"{number}번은", f"{number}번의") for number in range(2, count + 1))
    return [{"key": key, "mark": mark, "name": name, "topic": topic, "own": own}
            for key, (mark, name, topic, own) in zip(PREFIXES, names)]


COUNT_WORDS = {2: ("둘", "두"), 3: ("셋", "세"), 4: ("넷", "네")}
templates.env.globals["roster"] = roster
templates.env.globals["count_words"] = COUNT_WORDS

GRID_START_HOUR = 6
GRID_END_HOUR = 24
GRID_ROW_H = 44
GRID_HOURS = tuple(f"{hour:02d}" for hour in range(GRID_START_HOUR, GRID_END_HOUR))


def _grid_offset(minute: int) -> int:
    return max(0, (minute - GRID_START_HOUR * 60) * GRID_ROW_H // 60)


def build_board(group) -> dict[str, object]:
    """Place a group's classes on a week grid: columns are weekdays, each split into one lane per person."""
    blocks = []
    for lane, course in enumerate(group.courses):
        for day in course.days:
            if day not in DAYS:
                continue
            top = _grid_offset(course.start)
            blocks.append({
                "lane": lane,
                "day_index": DAYS.index(day),
                "top": top,
                "height": max(20, _grid_offset(course.end) - top),
                "name": course.name,
                "sport": course.sport,
                "time": f"{format_clock(course.start)}–{format_clock(course.end)}",
                "code": course.code,
                "audience": course.audience,
                "fee": course.monthly_fee,
            })
    overlaps = []
    for day in group.days:
        start = max(course.start for course in group.courses)
        end = min(course.end for course in group.courses)
        if end > start:
            top = _grid_offset(start)
            overlaps.append({"day_index": DAYS.index(day), "top": top, "height": _grid_offset(end) - top})
    return {
        "blocks": blocks,
        "overlaps": overlaps,
        "lanes": len(group.courses),
        # With three or four lanes, days everyone shares get wider so each lane stays readable.
        "columns": " ".join(
            f"minmax(0, {len(group.courses) - 1 if day in group.days else 1}fr)" for day in DAYS),
        "hours": GRID_HOURS,
        "row_h": GRID_ROW_H,
        "height": (GRID_END_HOUR - GRID_START_HOUR) * GRID_ROW_H,
        "width": 100,
    }


def select_group(result, pick: str):
    """Pick the combination shown on the board; falls back to the cheapest result."""
    groups = result.simultaneous
    if pick:
        codes = tuple(pick.split(":"))
        for group in groups:
            if group.codes == codes:
                return group
    return groups[0] if groups else None


def group_rows(groups, base_query: str, selected) -> list[dict[str, object]]:
    rows = []
    for group in groups[:20]:
        token = ":".join(group.codes)
        rows.append({
            "group": group,
            "href": f"/plan?{base_query}&pick={token}" if base_query else f"/plan?pick={token}",
            "selected": group is selected,
        })
    return rows


def count_people(request: Request, *, explicit: bool = False) -> int:
    """How many people the query describes: the last prefix that has any key, at least two.

    On the input page an explicit ``people`` value (from the add/remove buttons) wins,
    so "한 사람 빼기" can hide a person whose fields were just submitted."""
    params = request.query_params
    if explicit and params.get("people", "").isdecimal():
        return min(MAX_PEOPLE, max(MIN_PEOPLE, int(params["people"])))
    present = [index for index, prefix in enumerate(PREFIXES) if any(key.startswith(prefix + "_") for key in params)]
    return max(MIN_PEOPLE, max(present, default=0) + 1)


def read_people(request: Request, count: int | None = None) -> tuple[Person, ...]:
    count = count or count_people(request)
    people = []
    for prefix in PREFIXES[:count]:
        params = request.query_params
        budget = params.get(f"{prefix}_budget", "").strip()
        if budget and (not budget.isascii() or not budget.isdecimal() or len(budget) > 10):
            raise ValueError("예산은 0원 이상의 정수로 입력해 주세요")
        people.append(Person(
            days=frozenset(params.getlist(f"{prefix}_days")),
            start=parse_clock(params.get(f"{prefix}_start", "18:00")),
            end=parse_clock(params.get(f"{prefix}_end", "22:00"), allow_midnight_end=True),
            sport=params.get(f"{prefix}_sport") or None,
            excluded_sports=frozenset(filter(None, params.getlist(f"{prefix}_exclude"))),
            max_monthly_fee=int(budget) if budget else None,
        ))
    return tuple(people)


def render(request: Request, name: str, *, status_code: int = 200, **context: object) -> HTMLResponse:
    courses = request.app.state.courses
    common = {
        "meta": request.app.state.meta, "source_url": SOURCE_URL,
        "disclaimer": DISCLAIMER, "days": DAYS,
        "sports": sorted({course.sport for course in courses}),
    }
    return templates.TemplateResponse(request=request, name=name, context={**common, **context}, status_code=status_code)


def create_app(database: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        db = database or Path(os.environ.get("KSPO_DB_PATH", str(DEFAULT_DB)))
        if not db.exists():
            ingest(FIXTURE, db)
        application.state.courses, application.state.meta = load_database(db)
        yield

    application = FastAPI(title="함께 운동 시간표", description="같이 가서, 각자 운동할 수 있을까요?", lifespan=lifespan)
    application.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")

    @application.get("/", response_class=HTMLResponse)
    def root(request: Request) -> HTMLResponse:
        try:
            example = {"1": DEMO, "3": DEMO_GROUP}.get(request.query_params.get("example", ""))
            people = example or read_people(request, count_people(request, explicit=True))
        except ValueError as error:
            return render(request, "error.html", error=str(error), status_code=422)
        # Someone was just removed with "한 사람 빼기": offer the way back, values intact.
        submitted = count_people(request)
        restore = None
        if not example and submitted > len(people):
            query = [(key, value) for key, value in request.query_params.multi_items() if key != "people"]
            restore = "/?" + urlencode(query + [("people", str(submitted))])
        return render(request, "index.html", people=people, restore=restore, submitted=submitted,
                      max_people=MAX_PEOPLE, min_people=MIN_PEOPLE)

    @application.get("/plan", response_class=HTMLResponse)
    def results(request: Request) -> HTMLResponse:
        try:
            people = read_people(request)
        except ValueError as error:
            return render(request, "error.html", error=str(error), status_code=422)
        result = plan(request.app.state.courses, *people)
        share = str(request.base_url).rstrip("/") + plan_url(people)
        selected = select_group(result, request.query_params.get("pick", ""))
        base_query = plan_url(people).removeprefix("/plan?").removeprefix("?")
        return render(
            request,
            "plan.html",
            people=people,
            result=result,
            share=share,
            edit_url="/" + plan_url(people).removeprefix("/plan"),
            simultaneous_rows=group_rows(result.simultaneous, base_query, selected),
            board=build_board(selected) if selected else None,
            selected=selected,
        )

    @application.get("/evidence", response_class=HTMLResponse)
    def evidence(request: Request, a_code: str | None = None, b_code: str | None = None,
                 c_code: str | None = None, d_code: str | None = None) -> HTMLResponse:
        selected = []
        given = [a_code, b_code, c_code, d_code]
        if any(given):
            count = max(index for index, code in enumerate(given) if code) + 1
            codes = given[:max(MIN_PEOPLE, count)]
            if not all(codes) or len(set(codes)) != len(codes):
                raise HTTPException(400, "서로 다른 강좌번호가 사람 수만큼 필요합니다")
            by_code = {course.code: course for course in request.app.state.courses}
            if any(code not in by_code for code in codes):
                raise HTTPException(404, "기준 월에 없는 강좌번호입니다")
            selected = [by_code[code] for code in codes]
            full = Person(frozenset(DAYS), 0, 1440)
            groups = search(tuple(selected), *(full,) * len(selected))
            if not any(group.codes == tuple(codes) for group in groups.simultaneous):
                raise HTTPException(422, "공통 요일과 마치는 시각이 같은 강좌 조합이 없습니다")
        return render(request, "evidence.html", selected=selected)

    @application.get("/meta")
    def meta(request: Request) -> dict[str, str | int]:
        return request.app.state.meta

    @application.get("/health")
    def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str | bool]:
        return {"status": "ok", "data_go_kr_key_configured": settings.key_configured}

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> HTMLResponse:
        return render(request, "error.html", error=error.detail, status_code=error.status_code)

    return application


app = create_app()
