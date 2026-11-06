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
from app.planner import Person, plan, search

DISCLAIMER = "정원은 잔여석이 아니며 수강 신청 가능 여부를 보장하지 않습니다."
DEMO = (
    Person(frozenset(("화", "목")), 1080, 1140, max_monthly_fee=100000),
    Person(frozenset(("화", "목")), 1080, 1140, max_monthly_fee=70000),
)
templates = Jinja2Templates(directory=ROOT / "app/templates")
templates.env.filters["clock"] = format_clock
templates.env.filters["money"] = lambda value: f"{value:,}"


def plan_url(people: tuple[Person, Person]) -> str:
    params: list[tuple[str, str]] = []
    for prefix, person in zip(("a", "b"), people):
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

GRID_START_HOUR = 6
GRID_END_HOUR = 24
GRID_ROW_H = 44
GRID_HOURS = tuple(f"{hour:02d}" for hour in range(GRID_START_HOUR, GRID_END_HOUR))


def _grid_offset(minute: int) -> int:
    return max(0, (minute - GRID_START_HOUR * 60) * GRID_ROW_H // 60)


def build_board(pair) -> dict[str, object]:
    """Place a pair's classes on a week grid: columns are weekdays, rows are hours."""
    blocks = []
    for person, course in (("A", pair.a), ("B", pair.b)):
        for day in course.days:
            if day not in DAYS:
                continue
            top = _grid_offset(course.start)
            blocks.append({
                "person": person,
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
    for day in pair.days:
        start, end = max(pair.a.start, pair.b.start), min(pair.a.end, pair.b.end)
        if end > start:
            top = _grid_offset(start)
            overlaps.append({"day_index": DAYS.index(day), "top": top, "height": _grid_offset(end) - top})
    return {
        "blocks": blocks,
        "overlaps": overlaps,
        "hours": GRID_HOURS,
        "row_h": GRID_ROW_H,
        "height": (GRID_END_HOUR - GRID_START_HOUR) * GRID_ROW_H,
        "width": 100,
    }


def select_pair(result, pick: str):
    """Pick the combination shown on the board; falls back to the cheapest result."""
    pairs = (*result.simultaneous, *result.consecutive)
    if pick:
        left, _, right = pick.partition(":")
        for pair in pairs:
            if {left, right} == {pair.a.code, pair.b.code}:
                return pair
    return pairs[0] if pairs else None


def pair_rows(pairs, base_query: str, selected) -> list[dict[str, object]]:
    rows = []
    for pair in pairs[:20]:
        token = f"{pair.a.code}:{pair.b.code}"
        rows.append({
            "pair": pair,
            "href": f"/plan?{base_query}&pick={token}" if base_query else f"/plan?pick={token}",
            "selected": pair is selected,
        })
    return rows


def read_people(request: Request) -> tuple[Person, Person]:
    people = []
    for prefix in ("a", "b"):
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
    return people[0], people[1]


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
            people = DEMO if request.query_params.get("example") == "1" else read_people(request)
        except ValueError as error:
            return render(request, "error.html", error=str(error), status_code=422)
        return render(request, "index.html", people=people)

    @application.get("/plan", response_class=HTMLResponse)
    def results(request: Request) -> HTMLResponse:
        try:
            people = read_people(request)
        except ValueError as error:
            return render(request, "error.html", error=str(error), status_code=422)
        result = plan(request.app.state.courses, *people)
        share = str(request.base_url).rstrip("/") + plan_url(people)
        selected = select_pair(result, request.query_params.get("pick", ""))
        base_query = plan_url(people).removeprefix("/plan?").removeprefix("?")
        return render(
            request,
            "plan.html",
            people=people,
            result=result,
            share=share,
            edit_url="/" + plan_url(people).removeprefix("/plan"),
            simultaneous_rows=pair_rows(result.simultaneous, base_query, selected),
            consecutive_rows=pair_rows(result.consecutive, base_query, selected),
            board=build_board(selected) if selected else None,
            selected=selected,
        )

    @application.get("/evidence", response_class=HTMLResponse)
    def evidence(request: Request, a_code: str | None = None, b_code: str | None = None) -> HTMLResponse:
        selected = []
        if a_code or b_code:
            if not a_code or not b_code or a_code == b_code:
                raise HTTPException(400, "서로 다른 강좌번호 두 개가 필요합니다")
            by_code = {course.code: course for course in request.app.state.courses}
            if a_code not in by_code or b_code not in by_code:
                raise HTTPException(404, "기준 월에 없는 강좌번호입니다")
            selected = [by_code[a_code], by_code[b_code]]
            full = Person(frozenset(DAYS), 0, 1440)
            pairs = search(tuple(selected), full, full)
            if not pairs.simultaneous and not pairs.consecutive:
                raise HTTPException(422, "공통 요일과 60분 이내 시간 관계가 없는 강좌입니다")
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
