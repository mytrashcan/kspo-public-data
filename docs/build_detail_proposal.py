"""상세 기획서 생성기 (간결본) — 2026년도 공공데이터 활용 경진대회.

요약 1장 + 본문 6장 + 부록 1장. 중복 섹션 없이 한 번씩만 쓴다.

실행:
  /usr/local/bin/python3 build_lean_proposal.py <out.docx> [figs_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

INK = (0x12, 0x14, 0x1A)
MUTED = (0x5B, 0x60, 0x68)
ACCENT = (0x1B, 0x3F, 0xA8)
FONT = "맑은 고딕"
PAIR_WIDTH = Cm(7.0)


def _setup_page(doc):
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(1.9)
        section.bottom_margin = Cm(1.9)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def _font(run, size=10.5, bold=False, color=None):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def h(doc, text, level=1):
    sizes = {1: 14, 2: 11.5}
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    para.paragraph_format.space_after = Pt(4)
    para.paragraph_format.line_spacing = Pt(sizes[level] * 1.4)
    para.paragraph_format.keep_with_next = True
    _font(para.add_run(text), size=sizes[level], bold=True, color=ACCENT if level == 1 else INK)
    return para


def p(doc, text="", size=10.5, bold=False, color=None, indent=0.0, after=4):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(after)
    para.paragraph_format.line_spacing = Pt(size * 1.42)
    if indent:
        para.paragraph_format.left_indent = Cm(indent)
    if text:
        _font(para.add_run(text), size=size, bold=bold, color=color)
    return para


def bullets(doc, items, size=10.5):
    for item in items:
        para = doc.add_paragraph(style="List Bullet")
        para.paragraph_format.space_after = Pt(1)
        para.paragraph_format.line_spacing = Pt(size * 1.4)
        _font(para.add_run(item), size=size)


def table(doc, rows, widths=None, size=9.5):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j, value in enumerate(row):
            cells[j].text = ""
            para = cells[j].paragraphs[0]
            para.paragraph_format.space_after = Pt(1)
            para.paragraph_format.line_spacing = Pt(size * 1.35)
            _font(para.add_run(str(value)), size=size, bold=(i == 0))
            if widths:
                cells[j].width = Cm(widths[j])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure_grid(doc, items, cols=2):
    items = [(path, caption) for path, caption in items if path.exists()]
    if not items:
        return
    rows = (len(items) + cols - 1) // cols
    grid = doc.add_table(rows=rows * 2, cols=cols)
    for index, (path, caption) in enumerate(items):
        cell = grid.cell((index // cols) * 2, index % cols)
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(str(path), width=PAIR_WIDTH)
        cap = grid.cell((index // cols) * 2 + 1, index % cols).paragraphs[0]
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _font(cap.add_run(caption), size=8.5, color=MUTED)


def build(out: str, figs: Path) -> None:
    doc = Document()
    _setup_page(doc)

    # ---------------- 요약서 ----------------
    p(doc, "2026년도 공공데이터 활용 경진대회 · 상세 기획서", size=9, color=MUTED, after=1)
    p(doc, "함께 운동 시간표", size=19, bold=True, color=ACCENT, after=1)
    p(doc, "같이 가서, 각자 운동할 수 있을까요?", size=10, color=MUTED, after=8)
    h(doc, "기획 요약서", 1)

    h(doc, "1. 활용사례명", 2)
    p(doc, "함께 운동 시간표 — 2~4명이 같은 날 각자 다른 운동을 할 수 있는지 계산하고, 안 되면 무엇을 얼마나 바꾸면 되는지 제시하는 서비스", indent=0.4)

    h(doc, "2. 사용한 공공데이터명", 2)
    p(doc, "한국체육산업개발주식회사_일산스포츠센터 강좌정보 (공공데이터포털 15114776, 파일데이터·CSV·연간 갱신)", indent=0.4)

    h(doc, "3. 요약", 2)
    p(doc, "같이 운동하러 가려는 2~4명이 각자의 가능한 요일·시간·예산을 넣으면, 실제 강좌 데이터로 같은 요일에 마치는 시각이 같고 수업이 겹치는 조합을 회비 순으로 계산합니다. "
           "조합이 없으면 요일 추가·예산 증액·시간창 확장·종목 완화 중 가장 작은 변경을 계산하고, 바꾼 조건으로 다시 검색해 실제로 성립하는 것만 보여줍니다. "
           "모든 결과에 강좌번호, 데이터 기준월, 원본 CSV 행이 붙어 근거를 화면에서 확인할 수 있습니다.", indent=0.4)

    h(doc, "4. 기대효과", 2)
    p(doc, "강좌 표를 오가며 시간과 회비를 대조하던 일을 입력 한 번으로 줄이고, 성립하지 않는 조건은 '무엇을 바꾸면 되는지'로 바꿔줍니다. "
           "공개된 강좌정보 한 종류만 쓰므로 다른 센터로 넓히기 쉽고, 유료·비공개 데이터가 필요 없습니다.", indent=0.4)

    doc.add_page_break()

    # ---------------- 1. 개요 ----------------
    h(doc, "1. 활용사례 개요", 1)
    h(doc, "1-1. 활용사례 명", 2)
    p(doc, "함께 운동 시간표", indent=0.4)

    h(doc, "1-2. 기능", 2)
    bullets(doc, [
        "조건 입력: 2~4명의 가능한 요일, 시간 범위, 선호·제외 종목, 월 회비 상한을 한 화면에서 입력합니다. 인원은 '한 사람 더' 버튼으로 늘리고, 입력값은 유지됩니다.",
        "결과: 같은 요일에 마치는 시각이 같고 수업이 겹치는 조합을 합계 회비 순으로 제시합니다. 조합을 고르면 주간 시간표에 사람별 레인과 겹치는 구간이 그려집니다.",
        "최소 변경 제안: 조합이 없을 때 가장 작은 변경과 그 비용을 계산하고, 바꾼 조건으로 다시 검색해 성립하는 것만 표시합니다.",
        "원문 근거: 선택한 강좌들의 원본 CSV 행, 파일 해시, 수집 시각, 데이터 기준월을 보여줍니다.",
    ])

    figure_grid(doc, [
        (figs / "pair" / "home.png", "[그림 1] 조건 입력"),
        (figs / "pair" / "plan.png", "[그림 2] 2인 결과 — 사람별 레인"),
        (figs / "pair" / "three.png", "[그림 3] 3인 결과"),
        (figs / "pair" / "evidence.png", "[그림 4] 원문 근거"),
    ])

    h(doc, "1-3. 서비스 확인 방법", 2)
    p(doc, "로그인 없이 아래 주소에서 바로 확인할 수 있습니다.", after=3)
    table(doc, [
        ["확인 항목", "주소"],
        ["첫 화면", "https://kspo.dcselfie.win"],
        ["2인 결과", "https://kspo.dcselfie.win/plan?a_days=화&a_days=목&a_start=18:00&a_end=19:00&a_budget=100000&b_days=화&b_days=목&b_start=18:00&b_end=19:00&b_budget=70000"],
        ["3인 결과", "https://kspo.dcselfie.win/plan?a_sport=검도&a_days=월&a_days=화&a_days=수&a_days=목&a_days=금&a_start=21:00&a_end=22:00&b_sport=배드민턴&b_days=월&b_days=화&b_days=수&b_days=목&b_days=금&b_start=19:00&b_end=22:00&c_sport=스쿼시&c_days=화&c_days=목&c_days=토&c_days=일&c_start=21:00&c_end=22:00"],
        ["원문 근거", "https://kspo.dcselfie.win/evidence?a_code=1029879&b_code=21832"],
    ], widths=[2.8, 12.4], size=8.5)

    # ---------------- 2. 독창성 ----------------
    h(doc, "2. 활용사례의 독창성", 1)
    h(doc, "2-1. 활용 공공데이터", 2)
    table(doc, [
        ["데이터셋", "활용 필드", "활용 방식"],
        ["일산스포츠센터 강좌정보 (15114776)", "강좌번호, 시작월, 종목, 강좌명, 시작종료시간, 요일, 금액, 강습반",
         "요일·시간 겹침 판정, 월 회비 합산, 최소 변경 계산, 원문 근거 제시 (계산의 필수 입력)"],
    ], widths=[4.6, 5.4, 5.2])

    h(doc, "2-2. 배경과 차별점", 2)
    p(doc, "공모 안내문의 예시는 공연 알림, 혼잡도 예측, 실감형 콘텐츠였고, 기관이 이미 하는 안내 서비스와 겹치지 않는 축으로 '같이 갈 수 있는가'를 골랐습니다. "
           "이 질문은 예측이 아니라 계산이라 결과를 검증할 수 있습니다.", after=4)
    bullets(doc, [
        "두 사람의 시간표를 눈으로 대조하던 일을 계산으로 바꿉니다. 마치는 시각이 같아야 '같이 나온다'가 성립한다는 조건을 규칙으로 고정했습니다.",
        "성립하지 않는 조건을 정보로 바꿉니다. 요일 1개 추가, 예산 5,000원 증액처럼 최소 변경과 비용을 제시하고, 제안을 재검색으로 검증합니다.",
        "결과를 원문까지 소급합니다. 화면의 모든 조합은 강좌번호와 원본 CSV 행, 파일 해시로 확인됩니다.",
        "없는 값을 만들지 않습니다. 정원을 잔여석으로 읽지 않고, 대기시간·신청 가능 여부를 표시하지 않으며, 그 이유를 화면에 밝힙니다.",
    ])

    h(doc, "2-3. 실측", 2)
    table(doc, [
        ["항목", "값"],
        ["원본", "17,146행 → 파싱 성공 17,073행 (실패 73건)"],
        ["기준월 2026-10 강좌", "155개 / 15종목 (스쿼시 48, 기구필라테스 40, TRX 12, 농구 9)"],
        ["월 회비 범위", "21,000원 ~ 160,000원 (중앙값 70,000원)"],
        ["같은 종료 시각 묶음", "76개"],
        ["2인 조합 / 3인 조합", "494쌍 / 37건 이상 (예: 검도+배드민턴+스쿼시, 화·목 21:50 종료, 197,000원)"],
    ], widths=[4.4, 10.8])

    # ---------------- 3. 구체성 ----------------
    h(doc, "3. 활용사례의 구체성", 1)
    h(doc, "3-1. 처리 흐름", 2)
    table(doc, [
        ["단계", "내용"],
        ["수집", "공공데이터포털에서 CSV를 내려받아 파일 해시와 함께 고정"],
        ["정규화", "요일 문자열을 집합으로, '19:00~21:50'을 분 단위로 변환. 실패는 사유별로 집계"],
        ["적재", "기준월(2026-10)만 사용해 SQLite에 적재, 원본 행 번호 보존"],
        ["계산", "사람별 조건으로 강좌를 추린 뒤, 같은 종료 시각 묶음에서 서로 다른 강좌를 하나씩 골라 조합 생성"],
        ["제시", "합계 회비 → 겹침 → 강좌번호 순 정렬, 상위 결과를 주간 시간표로 렌더"],
    ], widths=[2.6, 12.6])

    h(doc, "3-2. 조합 판정 규칙", 2)
    p(doc, "조합은 다음을 모두 만족할 때만 성립합니다.", after=3)
    bullets(doc, [
        "사람 수만큼 서로 다른 강좌를 하나씩 쓴다(같은 강좌를 두 사람이 함께 쓰지 않음).",
        "모든 강좌의 공통 요일이 하나 이상 있다.",
        "모든 강좌의 종료 시각이 같다. 함께 도착해 함께 나올 수 있어야 '같이 운동'이 되기 때문이다.",
        "겹침 = 종료 시각 − (시작 시각 중 가장 늦은 값) 으로 계산한다.",
    ])
    table(doc, [
        ["입력", "판정"],
        ["두 사람 모두 화·목 18:00~19:00", "성립 — TRX 18:00–18:50 + 농구 18:00–18:50, 135,000원"],
        ["종료 시각이 다름", "불성립 — 먼저 끝난 사람이 기다려야 함"],
        ["공통 요일 없음", "불성립 — 요일 추가를 최소 변경으로 제안"],
    ], widths=[6.0, 9.2])

    h(doc, "3-3. 최소 변경 계산", 2)
    p(doc, "요일 1개 추가 / 회비 상한 증액 / 시간창 확장 / 종목 제한 완화의 네 가지만 시도합니다. 각 변경은 필요한 최소량을 계산하고, 그 변경을 적용해 다시 검색해 조합이 실제로 나타날 때만 제안합니다.", after=3)
    table(doc, [
        ["예시", "결과"],
        ["짝의 회비 상한 70,000원 → 75,000원", "TRX 42,000원 + 농구 55,000원 조합 등장, 여기서 멈춤"],
    ], widths=[6.4, 8.8])

    h(doc, "3-4. 데이터 함정과 대응", 2)
    table(doc, [
        ["함정", "대응"],
        ["'시작일'에 기간 문자열(2026-10-01~9999-12-31)과 실제 시작일이 섞임", "날짜 필드를 신뢰하지 않고 기준월은 '시작월'로 판정"],
        ["'정원'은 잔여석이 아님", "잔여석·신청 가능 여부를 계산·표시하지 않고, 화면에 그 사실을 명시(테스트로 금지)"],
        ["금액의 과금 주기 미표기", "월 회비로 해석해 표시하되 해석임을 병기"],
        ["'강습반' 표기가 거침(155개 중 115개가 '성인남여및청소년')", "연령·성별 자격을 판정하지 않고 원문 라벨 그대로 표시"],
        ["일부 강좌가 2시간 50분(배드민턴 19:00–21:50)", "수업 길이를 가정하지 않고 원문 시각만 사용"],
    ], widths=[7.6, 7.6])

    h(doc, "3-5. 검증", 2)
    bullets(doc, [
        "자동 테스트 90건: 파서 함정, 요일·시간 파싱, 2·3·4인 조합, 최소 변경 4유형, 인원 추가·삭제, 화면·API 응답, 금지 문구 가드.",
        "실데이터 확인: 155개 강좌에서 494쌍(2인)·37건 이상(3인)이 성립하고, 대표 조합의 금액·시각이 원본 행과 일치.",
        "금지 문구 가드: '잔여석', '신청 가능', '대기' 같은 단어가 화면·응답에 등장하면 테스트가 실패.",
    ])

    # ---------------- 4. 적절성 ----------------
    h(doc, "4. 사례의 활용 적절성", 1)
    h(doc, "4-1. 사회적 가치", 2)
    p(doc, "부모와 성인 자녀, 부부, 친구가 같은 시간에 각자 운동하려면 지금은 각자 시간표를 열어 눈으로 맞춰야 합니다. "
           "이 서비스는 그 대조를 한 번의 조회로 줄이고, 조건이 안 맞을 때 포기하지 않도록 '무엇을 바꾸면 되는지'까지 제시합니다.", after=4)
    table(doc, [
        ["항목", "내용"],
        ["1차 사용자", "일산스포츠센터 강좌를 함께 들으려는 성인 2~4인 (강습반 155개 중 115개가 성인 대상 표기)"],
        ["줄이는 일", "강좌 표를 오가며 시간·회비를 대조하던 작업 → 입력 1회"],
        ["공공데이터 활용", "공개 강좌정보 1종만 사용, 유료·비공개 데이터 불필요 (활용신청 299건으로 아직 덜 쓰인 데이터)"],
        ["확장", "올림픽(15110953)·분당(15118652) 강좌정보를 같은 형식으로 추가 가능"],
    ], widths=[3.4, 11.8])

    # ---------------- 5. 실현가능성 ----------------
    h(doc, "5. 실현가능성 및 기타", 1)
    h(doc, "5-1. 추진 일정", 2)
    table(doc, [
        ["기간", "내용", "상태"],
        ["2026-11-06", "데이터 접근성·신선도 검증, 조합 계산 게이트 통과", "완료"],
        ["2026-11", "서비스 구현·배포, 테스트 90건, 기획서·시연 영상", "완료"],
        ["2026-12-01", "참가신청서·기획서 제출", "예정"],
        ["2026-12 ~", "심사 대응, 문의 대응", "예정"],
        ["2027 ~ 2028", "데이터 연 1회 갱신, 다른 센터 확장, 운영 유지", "예정"],
    ], widths=[3.0, 9.6, 2.6])

    h(doc, "5-2. 개발·운영 계획", 2)
    table(doc, [
        ["항목", "내용"],
        ["구성", "FastAPI + SQLite + Jinja2, 별도 프런트엔드 빌드 없음"],
        ["배포", "OCI ARM 1대(2 OCPU·12GB)에서 systemd로 구동, 기존 서비스와 함께 동작"],
        ["데이터 갱신", "연 1회 공개 파일 교체 → 적재 1회 실행, 해시·기준월 자동 기록"],
        ["비용", "추가 서버·유료 API 없음"],
    ], widths=[3.2, 12.0])

    h(doc, "5-3. 2028년까지 운영 가능 여부", 2)
    p(doc, "가능합니다. 외부 유료 의존성이 없고, 데이터가 연 1회 갱신되므로 적재 1회로 유지됩니다. "
           "화면에 데이터 기준월을 항상 표시해 갱신이 늦어져도 상태를 알 수 있습니다.", after=3)
    table(doc, [
        ["리스크", "대응"],
        ["데이터 갱신 지연", "기준월 표시, 마지막 정상 적재본 유지"],
        ["필드 구성 변경", "누락 사유별 탈락 건수 기록, 기준을 벗어나면 적재 중단"],
        ["서버 장애", "systemd 자동 재시작, 상태 확인 엔드포인트"],
        ["운영 인계", "실행·배포·수집 절차와 테스트를 저장소 문서로 유지"],
    ], widths=[5.6, 9.6])

    h(doc, "5-4. 추가 개방이 필요한 공공데이터 의견", 2)
    bullets(doc, [
        "잔여석·수강 상태: 이 서비스가 답하지 못하는 유일한 질문입니다. 현재 데이터에는 정원만 있어 신청 가능 여부를 알 수 없습니다.",
        "강좌별 실제 진행 기간: '시작일' 필드에 기간 문자열과 실제 시작일이 섞여 있어 정규화가 필요합니다.",
        "센터별 동일 스키마: 올림픽·분당 강좌정보가 같은 컬럼 구성을 쓰면 로더 추가만으로 확장됩니다.",
    ])

    # ---------------- 부록 ----------------
    h(doc, "부록. 사용한 데이터 필드 해석", 1)
    table(doc, [
        ["필드", "해석", "비고"],
        ["일련번호", "행 식별자", "조합 계산에 사용하지 않음"],
        ["강좌번호", "강좌 식별자", "근거 링크 키"],
        ["시작월", "강좌 기준월", "최신 기준월(2026-10)만 사용"],
        ["종목", "운동 종목", "선호·제외 조건 단위"],
        ["강좌명", "표시용 이름", "그대로 표시"],
        ["시작종료시간", "수업 시각 범위", "분 단위로 변환"],
        ["정원", "모집 정원", "잔여석 아님 — 계산 금지"],
        ["요일", "수업 요일", "집합으로 변환"],
        ["강습반", "대상 표기", "원문 그대로"],
        ["금액", "월 회비", "과금 주기 미표기"],
        ["시작일", "기간 문자열 혼입", "날짜로 신뢰하지 않음"],
        ["종료일", "실제 시작일이 섞임", "사용하지 않음"],
        ["링크", "원문 URL", "근거 화면에서 사용"],
    ], widths=[3.4, 4.8, 6.8], size=9)

    doc.save(out)
    print("saved", out)


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "상세기획서.docx"
    figs_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("figs")
    build(out_path, figs_path)
