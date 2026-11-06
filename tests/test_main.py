from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.ingest import FIXTURE, ingest
from app.main import DEMO, DISCLAIMER, app, create_app, plan_url


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("key, configured", [("", False), ("   ", False), ("test-only", True)])
def test_health(monkeypatch: pytest.MonkeyPatch, key: str, configured: bool) -> None:
    monkeypatch.setenv("DATA_GO_KR_KEY", key)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data_go_kr_key_configured": configured}
    assert "test-only" not in response.text


def test_root_is_korean_input_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "함께 운동 시간표" in response.text
    assert "예시 채우기" in response.text
    assert 'name="a_days"' in response.text
    assert client.get("/static/style.css").status_code == 200


class FormValues(HTMLParser):
    """Read a real GET form as the browser would submit it."""

    def __init__(self) -> None:
        super().__init__()
        self.values: list[tuple[str, str]] = []
        self.select_name = ""
        self.option: dict[str, str | None] | None = None
        self.option_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "input" and "name" in attributes:
            if attributes.get("type") not in ("checkbox", "radio") or "checked" in attributes:
                self.values.append((attributes["name"], attributes.get("value", "")))
        elif tag == "select":
            self.select_name = attributes["name"]
        elif tag == "option":
            self.option, self.option_text = attributes, ""

    def handle_data(self, data: str) -> None:
        if self.option is not None:
            self.option_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self.option is not None:
            if "selected" in self.option:
                self.values.append((self.select_name, self.option.get("value", self.option_text)))
            self.option = None
        elif tag == "select":
            self.select_name = ""


def test_one_click_demo_submits_actual_form(client: TestClient) -> None:
    page = client.get("/?example=1")
    parser = FormValues()
    parser.feed(page.text)
    from urllib.parse import urlencode
    response = client.get("/plan?" + urlencode(parser.values))
    assert response.status_code == 200
    for evidence in ("같은 시간에 각자", "TRX", "농구", "100,000원", "35,000원", "135,000원", "1029879", "21832", "18:00–18:50", "강습반 원문"):
        assert evidence in response.text
    assert '기구필라 18시(화목)' not in response.text


def test_plan_share_url_reproduces_state(client: TestClient) -> None:
    response = client.get(plan_url(DEMO))
    match = response.text.split('aria-label="공유 URL"')[0].rsplit('value="', 1)[1].split('"', 1)[0]
    shared = unescape(match)
    assert client.get(shared).text == response.text
    params = parse_qs(urlsplit(shared).query)
    assert params["a_days"] == ["화", "목"]
    assert params["b_budget"] == ["70000"]


def test_meta_is_provenance_of_loaded_fixture(client: TestClient) -> None:
    meta = client.get("/meta")
    assert meta.status_code == 200
    data = meta.json()
    assert data["as_of_month"] == "2026-10"
    assert data["dataset_id"] == "15114776"
    assert data["course_count"] == 155
    assert len(data["file_hash"]) == 64
    assert data["generated_at"]
    assert data["source_file_name"] == FIXTURE.name


def test_evidence_preserves_raw_quirks(client: TestClient) -> None:
    response = client.get("/evidence?a_code=1029879&b_code=21832")
    assert response.status_code == 200
    for value in ("2026-10-01~9999-12-31", "2026-10-01", "성인남여", "청소년", "100000", "35000", "시작일", "종료일", "이용허락", "15114776"):
        assert value in response.text
    assert client.get("/evidence?a_code=unknown&b_code=21832").status_code == 404
    assert client.get("/evidence?a_code=21832&b_code=21832").status_code == 400
    assert client.get("/evidence?a_code=1029879&b_code=21831").status_code == 422
    missing = client.get("/missing")
    assert missing.status_code == 404
    assert DISCLAIMER in missing.text


def test_user_input_is_escaped(client: TestClient) -> None:
    response = client.get("/plan", params={"a_sport": "<script>alert(1)</script>"})
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text


@pytest.mark.parametrize("url", ["/", "/?example=1", plan_url(DEMO), "/evidence", "/evidence?a_code=1029879&b_code=21832", "/plan?a_budget=-1", "/plan"])
def test_no_unsupported_claims_except_required_disclaimer(client: TestClient, url: str) -> None:
    page = client.get(url).text
    assert page.count(DISCLAIMER) == 1
    assert "데이터 기준 2026-10" in page
    assert "data.go.kr 15114776" in page
    body_without_disclaimer = page.replace(DISCLAIMER, "")
    for forbidden in ("잔여석", "신청 가능", "대기시간"):
        assert forbidden not in body_without_disclaimer


@pytest.mark.parametrize("query", ["a_start=25:00", "a_start=20:00&a_end=19:00", "a_days=휴일", "a_budget=-1", "b_budget=abc"])
def test_bad_inputs_are_readable_422(client: TestClient, query: str) -> None:
    response = client.get("/plan?" + query)
    assert response.status_code == 422
    assert "조건을 확인해 주세요" in response.text


def test_real_budget_relaxation_link_works(client: TestClient) -> None:
    from dataclasses import replace
    people = (replace(DEMO[0], sport="TRX", max_monthly_fee=95000), replace(DEMO[1], sport="농구"))
    response = client.get(plan_url(people))
    assert "최소 변경 제안" in response.text
    assert "월 5,000원 늘리면 성립" in response.text
    before = response.text.split("변경한 조건으로 다시 보기")[0]
    changed_url = unescape(before.rsplit('href="', 1)[1].split('"', 1)[0])
    assert "135,000원" in client.get(changed_url).text


def test_runtime_loader_uses_ingested_database(tmp_path: Path) -> None:
    import csv
    import io
    from app.ingest import parse_csv
    rows = [c.raw for c in parse_csv(FIXTURE.read_bytes()).courses if c.code in ("1029879", "21832")]
    for row in rows:
        row["시작월"] = "2026-11-01"
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    source, database = tmp_path / "runtime.csv", tmp_path / "runtime.sqlite3"
    source.write_bytes(buffer.getvalue().encode("cp949"))
    ingest(source, database)
    with TestClient(create_app(database)) as runtime:
        assert runtime.get("/meta").json()["as_of_month"] == "2026-11"
        assert runtime.get("/meta").json()["course_count"] == 2
        assert "데이터 기준 2026-11" in runtime.get(plan_url(DEMO)).text
