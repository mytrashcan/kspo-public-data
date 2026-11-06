"""상세 기획서 생성기 — 2026년도 공공데이터 활용 경진대회 (요약 1장 + 상세 10장 이내).

실행:
  /usr/local/bin/python3 build_detail_proposal.py <out.docx> [figs_dir]

figs_dir 에 home.png / plan.png / evidence.png 가 있으면 본문에 삽입한다.
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
FIG_WIDTH = Cm(15.2)


def _font(run, size=10.5, bold=False, color=None):
    run.font.name = "맑은 고딕"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def h(doc, text, level=1):
    sizes = {1: 15, 2: 12, 3: 11}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    _font(p.add_run(text), size=sizes[level], bold=True, color=ACCENT if level == 1 else INK)
    return p


def p(doc, text="", size=10.5, bold=False, color=None, indent=0.0, align=None, after=5):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(after)
    para.paragraph_format.line_spacing = 1.35
    if indent:
        para.paragraph_format.left_indent = Cm(indent)
    if align == "center":
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if text:
        _font(para.add_run(text), size=size, bold=bold, color=color)
    return para


def bullets(doc, items, size=10.5):
    for item in items:
        para = doc.add_paragraph(style="List Bullet")
        para.paragraph_format.space_after = Pt(2)
        para.paragraph_format.line_spacing = 1.3
        _font(para.add_run(item), size=size)


def numbered(doc, items, size=10.5):
    for item in items:
        para = doc.add_paragraph(style="List Number")
        para.paragraph_format.space_after = Pt(2)
        para.paragraph_format.line_spacing = 1.3
        _font(para.add_run(item), size=size)


def table(doc, rows, widths=None, header=True, size=9.5):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j, value in enumerate(row):
            cells[j].text = ""
            para = cells[j].paragraphs[0]
            para.paragraph_format.space_after = Pt(1)
            _font(para.add_run(str(value)), size=size, bold=(header and i == 0))
            if widths:
                cells[j].width = Cm(widths[j])
    doc.add_paragraph().paragraph_format.space_after = Pt(3)
    return t


def figure(doc, path: Path, caption: str) -> None:
    if not path.exists():
        p(doc, f"[그림 누락: {path.name}] {caption}", size=9, color=MUTED)
        return
    doc.add_picture(str(path), width=FIG_WIDTH)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p(doc, caption, size=9, color=MUTED, align="center", after=10)


def build(out: str, figs: Path) -> None:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "맑은 고딕"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    style.font.size = Pt(10.5)
    for section in doc.sections:
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)

    # ---------------- 표지 ----------------
    p(doc, "", after=60)
    p(doc, "2026년도 공공데이터 활용 경진대회", size=12, color=MUTED, align="center", after=6)
    p(doc, "상세 기획서", size=24, bold=True, align="center", after=10)
    p(doc, "함께 운동 시간표", size=20, bold=True, color=ACCENT, align="center", after=6)
    p(doc, "같이 가서, 각자 운동할 수 있을까요?", size=11, color=MUTED, align="center", after=40)
    table(doc, [
        ["구분", "내용"],
        ["활용사례명", "함께 운동 시간표"],
        ["활용 공공데이터", "한국체육산업개발주식회사_일산스포츠센터 강좌정보 (공공데이터포털 15114776)"],
        ["서비스 주소", "https://kspo.dcselfie.win"],
        ["개발 형태", "개인 참가 · 웹 서비스(서버 렌더링)"],
        ["제출일", "2026년 11월"],
    ], widths=[4.0, 12.0])
    doc.add_page_break()

    # ---------------- 기획 요약서 ----------------
    h(doc, "기획 요약서", 1)
    h(doc, "1. 활용사례명", 2)
    p(doc, "함께 운동 시간표 — 두 사람이 같은 날 각자 다른 운동을 할 수 있는지 계산하고, 성립하지 않으면 무엇을 얼마나 바꾸면 되는지 제시하는 서비스", indent=0.4)

    h(doc, "2. 사용한 공공데이터명", 2)
    p(doc, "한국체육산업개발주식회사_일산스포츠센터 강좌정보 (공공데이터포털 15114776, 파일데이터·CSV·연간 갱신)", indent=0.4)

    h(doc, "3. 요약", 2)
    p(doc, "두 사람이 각자의 가능한 요일·시간·월 예산을 입력하면, 일산스포츠센터의 실제 강좌 데이터로 같은 요일에 함께 갈 수 있는 조합을 계산합니다. "
           "같은 요일에 두 수업 시간이 겹치는 조합을 합계 월 회비 순으로 제시하고, 조건을 만족하는 조합이 없으면 요일 추가·예산 증액·시간 확장·종목 제한 완화 가운데 "
           "가장 작은 변경을 실제 강좌로 검증해 제안합니다. 모든 결과에는 강좌번호, 원문 강습반 표기, 데이터 기준월, 원본 CSV 행이 함께 표시되어 "
           "판단의 근거를 화면에서 확인할 수 있습니다.", indent=0.4)

    h(doc, "4. 기대효과", 2)
    bullets(doc, [
        "동행 운동을 계획할 때 각자 센터 시간표를 따로 확인하고 눈으로 대조하던 과정을 한 번의 조회로 줄입니다.",
        "개방된 파일데이터를 계산의 필수 입력으로 사용해, 목록 조회에 머물던 공공데이터 활용을 재사용 사례로 확장합니다.",
        "조건 비교 과정에서 평소 노출되지 않던 강좌가 드러나 센터의 강좌 운영과 홍보에도 도움이 됩니다.",
        "잔여석·수강 상태처럼 공개되지 않은 정보는 추정하지 않고 화면에 한계를 명시해, 이용자가 센터에 확인해야 할 사항을 분명히 합니다.",
    ])
    doc.add_page_break()

    # ---------------- 1. 개요 ----------------
    h(doc, "1. 활용사례 개요", 1)
    h(doc, "1-1. 활용사례 명", 2)
    p(doc, "함께 운동 시간표", indent=0.4)

    h(doc, "1-2. 활용사례 기능, 특징 등 세부내용", 2)
    p(doc, "서비스는 네 화면으로 구성되며, 모든 화면이 서버에서 렌더링되어 로그인과 설치가 필요하지 않습니다.")
    numbered(doc, [
        "조건 입력(첫 화면): A·B 두 사람의 가능한 요일, 시작·종료 시각, 선호 종목, 제외 종목, 최대 월 회비를 입력합니다. 요일과 종목은 한눈에 보이는 칩 형태로 배치해, 어떤 조건이 선택됐는지 즉시 확인됩니다.",
        "결과 화면: 같은 요일에 두 수업 시간이 겹치는 조합을 합계 월 회비 순으로 제시합니다. 조합을 선택하면 오른쪽 주간 시간표에 두 강좌가 실제 시각 위치의 블록으로 그려지고, 겹치는 구간이 해칭 밴드로 표시됩니다.",
        "최소 변경 제안: 조건을 만족하는 조합이 없을 때, 요일 추가·예산 증액·시간창 확장·종목 제한 완화 가운데 가장 작은 변경과 그 비용을 제시합니다. 제안은 변경된 조건으로 다시 검색해 실제 조합이 존재하는지 검증한 뒤에만 표시됩니다.",
        "원문 근거 화면: 선택한 두 강좌의 원본 CSV 행 전체, 입력 파일의 SHA-256, 수집 시각, 데이터 기준월을 표시합니다.",
    ])
    figure(doc, figs / "home.png", "[그림 1] 조건 입력 화면 — 요일과 종목을 칩으로 배치해 선택 상태가 한눈에 보입니다.")
    figure(doc, figs / "plan.png", "[그림 2] 결과 화면 — 선택한 조합이 주간 시간표에 A/B 블록과 겹침 밴드로 표시됩니다.")

    h(doc, "1-3. 활용사례 서비스 확인 방법", 2)
    p(doc, "로그인 없이 아래 주소에서 바로 확인할 수 있습니다.", after=4)
    table(doc, [
        ["확인 항목", "주소"],
        ["서비스 첫 화면", "https://kspo.dcselfie.win"],
        ["결과 화면 예시 (A·B 모두 화·목 18:00–19:00, 월 예산 100,000원·70,000원)",
         "https://kspo.dcselfie.win/plan?a_days=화&a_days=목&a_start=18:00&a_end=19:00&a_budget=100000&b_days=화&b_days=목&b_start=18:00&b_end=19:00&b_budget=70000"],
        ["원문 근거 화면 예시", "https://kspo.dcselfie.win/evidence?a_code=1029879&b_code=21832"],
        ["데이터 메타데이터(JSON)", "https://kspo.dcselfie.win/meta"],
    ], widths=[5.2, 10.6])
    p(doc, "결과 화면은 조건을 주소에 담고 있어 링크를 그대로 전달하면 같은 결과가 재현됩니다. 별도 앱 설치나 회원가입이 필요하지 않습니다.")
    figure(doc, figs / "evidence.png", "[그림 3] 원문 근거 화면 — 원본 CSV 행과 파일 해시, 수집 시각을 함께 표시합니다.")
    doc.add_page_break()

    # ---------------- 2. 독창성 ----------------
    h(doc, "2. 활용사례의 독창성", 1)
    h(doc, "2-1. 활용 공공데이터", 2)
    table(doc, [
        ["데이터셋", "활용 필드", "활용 방식", "비중"],
        ["일산스포츠센터 강좌정보 (15114776)",
         "강좌번호, 시작월, 종목, 강좌명, 시작종료시간, 요일, 강습반, 금액, 시작일, 종료일, 링크",
         "요일·시간 겹침 판정, 월 회비 합산, 최소 변경 계산, 원문 표시", "핵심(계산의 필수 입력)"],
        ["스포츠센터 강좌 정보 (15147992)",
         "종목, 강좌명, 링크, 등록일, 수정일",
         "강좌 소개·요금 안내 링크 연결(확장 대상)", "보조"],
        ["올림픽수영장·분당·올림픽스포츠센터 강좌정보 (15101610·15118652·15110953)",
         "동일 계열 필드", "센터 확장을 위한 로더 대상(현재는 일산 단일 센터)", "확장"],
    ], widths=[4.4, 4.6, 4.8, 2.0])
    p(doc, "강좌의 요일·시간·요금이 없으면 서비스가 성립하지 않습니다. 부가 기능으로 데이터를 곁들인 사례가 아니라, 공공데이터가 계산의 입력 그 자체인 사례입니다.")

    h(doc, "2-2. 사례를 활용하게 된 배경 및 활용 우수성", 2)
    p(doc, "[배경]", bold=True, after=3)
    p(doc, "공모전이 제시한 예시는 공연 알림, 혼잡도 예측·분산 안내, 실감형 콘텐츠 세 가지이며, 주최기관은 공연 일정과 예상 주차장 이용률을 안내하는 자체 서비스를 이미 운영하고 있습니다. "
           "같은 축에서 서비스를 만들면 기존 서비스와 비교되어 차별성이 드러나기 어렵습니다. 그래서 시설 운영 데이터 가운데 아직 화면으로 소비되지 않은 영역인 '강좌 시간표'를 골랐습니다. "
           "시간표는 시설의 하루를 그대로 담고 있지만, 지금까지는 사람이 두 사람의 시간표를 각자 열어 눈으로 대조해야 하는 정보였습니다.")
    p(doc, "[활용 실측 — 원문 데이터로 확인한 값]", bold=True, after=3)
    table(doc, [
        ["측정 항목", "실측값"],
        ["입력 파일", "17,146행(CP949, 2.9MB), 유효 파싱 17,073행"],
        ["분석 대상", "최신 강좌월 2026-10 기준 강좌 155개, 15종목, 월 회비 21,000원~160,000원"],
        ["같은 요일·같은 종료 시각에 서로 다른 종목이 있는 슬롯", "76개 (예: 화·목 18:50 종료 슬롯에 농구·TRX·기구필라테스)"],
        ["같은 요일·같은 종료 시각으로 성립하는 조합", "494쌍"],
        ["실행 예시", "A(TRX 18시, 월 100,000원) + B(농구 18시, 월 35,000원) = 합계 월 135,000원, 겹치는 시간 50분"],
    ], widths=[8.6, 6.6])
    p(doc, "[차별점]", bold=True, after=3)
    numbered(doc, [
        "결과를 원문까지 소급합니다. 화면의 모든 조합은 강좌번호와 원본 CSV 행, 파일 해시, 수집 시각으로 확인됩니다. 판단의 근거를 화면 안에서 닫았습니다.",
        "성립하지 않는 조건을 정보로 바꿉니다. 요일 1개 추가, 예산 5,000원 증액처럼 최소 변경과 그 비용을 계산하고, 제안한 변경으로 다시 검색해 실제 조합이 존재하는지 검증한 뒤 표시합니다.",
        "데이터의 함정을 화면에 명시합니다. 정원을 잔여석으로 해석하지 않고, 시작일 필드에 섞인 기간 문자열을 무시하며, 강습반 표기는 원문 그대로 보여줍니다. 데이터를 가장 잘 아는 주체가 심사기관이라는 점을 고려한 설계입니다.",
        "관측하지 않은 값을 추정하지 않습니다. 대기시간·만차 여부·수강 가능 여부를 만들어 표시하지 않으므로, 결과의 신뢰 범위가 명확합니다.",
    ])
    doc.add_page_break()

    # ---------------- 3. 구체성 ----------------
    h(doc, "3. 활용사례의 구체성", 1)
    h(doc, "3-1. 처리 흐름", 2)
    table(doc, [
        ["단계", "내용"],
        ["수집", "공공데이터포털에서 강좌정보 CSV를 내려받아 파일 해시와 함께 고정"],
        ["정규화", "시작월·요일·시작/종료 시각(분)·월 회비·강습반·원문 행을 타입 레코드로 변환, 누락 사유별 탈락 건수 기록"],
        ["저장", "SQLite에 최신 강좌월만 적재, 데이터셋 ID·파일명·SHA-256·유효행수·기준월·수집시각을 메타로 보관"],
        ["계산", "각자의 조건을 만족하는 강좌를 추린 뒤, 공통 요일과 종료 시각이 같고 수업 시간이 겹치는 조합만 골라 합계 월 회비 순으로 정렬"],
        ["조건 완화", "성립 조합이 없을 때 실제 조합을 기준으로 요일·예산·시간·종목 변경량을 역산하고, 변경된 조건으로 재검색해 검증"],
        ["표시", "결과 목록, 주간 시간표, 최소 변경 제안, 원문 근거 화면"],
    ], widths=[2.6, 12.8])

    h(doc, "3-2. 조합 판정 규칙", 2)
    bullets(doc, [
        "강좌에 적힌 모든 요일과 수업 시간이 각자의 조건 안에 들어와야 후보가 됩니다(부분 포함은 허용하지 않음).",
        "두 강좌는 서로 다르고, 같은 센터·같은 강좌월이어야 하며, 공통 요일이 최소 하나 있어야 합니다.",
        "같은 요일에 마치는 시각이 같고 수업 시간이 겹치는 경우만 조합으로 인정합니다. 두 사람이 함께 도착해 함께 나올 수 있어야 '같이 운동'이 성립하기 때문입니다. 마치는 시각이 다르거나 앞뒤로 이어지기만 하는 조합은 제외했습니다.",
        "정렬은 합계 월 회비 오름차순, 다음으로 겹침이 긴 순서입니다.",
    ])

    h(doc, "3-3. 최소 변경 계산", 2)
    bullets(doc, [
        "요일: 두 사람이 허용하지 않은 요일 중 실제 강좌가 사용하는 요일의 개수",
        "예산: 각자 예산 상한 대비 실제 월 회비 초과분의 합",
        "시간: 시작 시각을 앞당겨야 하는 분, 종료 시각을 늦춰야 하는 분의 합",
        "종목: 선호·제외 조건과 실제 강좌가 어긋난 인원 수",
        "유형별로 가장 작은 변경을 하나씩 제시하고, 한 유형만으로 성립하지 않으면 여러 변경을 함께 제시합니다. 모든 제안은 변경된 조건으로 재검색해 실제 조합이 확인된 경우에만 노출됩니다.",
    ])

    h(doc, "3-4. 데이터 함정과 대응", 2)
    table(doc, [
        ["발견한 함정", "대응"],
        ["시작일 필드에 '2026-10-01~9999-12-31' 형태의 기간 문자열이 들어 있고, 종료일 필드에는 실제 시작일이 들어 있음",
         "월 판정은 시작월 필드만 사용하고, 원문 값은 해석하지 않고 보존해 근거 화면에 그대로 노출"],
        ["정원 필드는 잔여석이 아님", "잔여석·신청 가능 여부를 계산·표시하지 않고, 화면에 그 사실을 명시(테스트로 금지)"],
        ["금액 필드의 과금 주기 미표기", "월 회비로 해석해 표시하되 '원본 금액 필드를 월 회비로 해석한 값'임을 병기"],
        ["강습반 표기가 거칢(155개 중 115개가 '성인남여및청소년')", "연령·성별 자격을 자동 판정하지 않고 원문 라벨을 그대로 표시"],
        ["페이지 설명문의 '2013년~2025년 8월' 문구가 실제 파일 최신월(2026-10)과 불일치",
         "설명문이 아니라 파일에서 계산한 기준월을 화면에 표시"],
    ], widths=[8.4, 6.8])

    h(doc, "3-5. 검증", 2)
    table(doc, [
        ["검증 항목", "내용"],
        ["자동 테스트", "파서 함정(기간 문자열·빈 값·인코딩), 요일·시간 파싱, 조합 성립·불성립, 최소 변경 4유형, 화면·API 응답"],
        ["금지 문구 가드", "화면에 '잔여석·신청 가능·대기시간'이 등장하면 실패(면책 문구 1곳만 예외)"],
        ["실데이터 검증", "전체 CSV 17,146행 인제스트 후 2026-10 강좌 155개로 조합 계산, 데모 조합이 원문 행과 일치"],
    ], widths=[3.6, 11.6])
    # ---------------- 4. 활용 적절성 ----------------
    h(doc, "4. 사례의 활용 적절성", 1)
    p(doc, "[사회적 가치]", bold=True, after=3)
    bullets(doc, [
        "동행 부담 완화: 부모와 자녀, 부부, 친구가 같은 시간에 각자 운동하려면 두 사람의 시간표를 각자 확인해 대조해야 합니다. 이 과정을 한 번의 조회로 줄입니다.",
        "운동 참여 장벽 완화: '함께 갈 수 있는 시간이 없다'는 판단을 '무엇을 바꾸면 가능한가'라는 판단으로 바꿉니다.",
        "센터 운영 지원: 상담 창구에서 반복되는 시간표 문의를 줄이고, 조건 비교 과정에서 평소 노출되지 않던 강좌가 드러납니다.",
        "공공데이터 활용 촉진: 조회·목록 소비에 머물던 시설 파일데이터를 계산의 입력으로 사용하는 사례를 만듭니다.",
    ])
    p(doc, "[한계와 정직한 범위]", bold=True, after=3)
    p(doc, "이 서비스는 수강 신청을 대신하지 않습니다. 공개 데이터에 잔여석과 수강 상태가 없으므로 신청 가능 여부를 판단하지 않으며, 화면에도 그 사실을 명시합니다. "
           "강습반 표기가 거칠어 연령 자격을 자동 판정하지 않고 원문을 그대로 보여줍니다. 따라서 이용자는 후보를 좁힌 뒤 센터에 확인하는 절차를 거치게 되며, "
           "이 확인 절차를 없애는 것을 목표로 삼지 않습니다. 데이터가 연 1회 갱신되므로, 화면에는 항상 계산에 사용한 기준월을 함께 표시합니다.")
    doc.add_page_break()

    # ---------------- 5. 실현가능성 ----------------
    h(doc, "5. 실현가능성 및 기타", 1)
    h(doc, "5-1. 추진 일정", 2)
    table(doc, [
        ["기간", "내용", "상태"],
        ["2026-11-06", "데이터 접근성·신선도 검증(강좌 155개, 최신 기준월 2026-10), 조합 계산 가능성 확인", "완료"],
        ["2026-11-06", "수집·정규화·조합 엔진·주간 시간표·근거 화면 구현, 자동 테스트", "완료"],
        ["2026-11-06", "공개 주소 배포(HTTPS), 데모 링크 재현 확인", "완료"],
        ["2026-11 중순", "다른 센터 강좌 데이터 확장, 사용성 검토 반영", "예정"],
        ["2026-11 말", "기능 동결, 시연 영상과 제출 서류 마무리", "예정"],
        ["2026-12-01", "접수 마감(이메일 제출)", "예정"],
    ], widths=[2.8, 10.8, 1.8])

    h(doc, "5-2. 개발·운영 계획", 2)
    bullets(doc, [
        "구성: Python 3.12, FastAPI, SQLite, Jinja2 서버 렌더링. 외부 유료 API·문자 발송·LLM 호출이 없어 운영 비용이 고정적입니다.",
        "배포: 소규모 클라우드 인스턴스 1대에서 systemd 서비스로 구동하며, 이 서비스가 추가로 사용하는 메모리는 512MB 이내입니다.",
        "데이터 갱신: 강좌정보는 연간 갱신 주기이므로, 갱신 파일을 받아 해시와 기준월을 갱신하고 재적재합니다. 갱신 파일이 없으면 마지막 정상 데이터를 유지하되 기준월을 함께 표시합니다.",
        "장애 대응: 적재 실패·스키마 변경 시 이전 적재본으로 동작하고, 화면 상단의 기준월로 상태를 알 수 있습니다.",
        "인수 가능성: 실행 방법, 데이터 수집 절차, 집계·계산 규칙, 테스트, 의존성 목록을 저장소 문서로 함께 제공합니다.",
    ])

    h(doc, "5-3. 2028년까지 운영 가능 여부", 2)
    p(doc, "가능합니다. 현재 소규모 클라우드 인스턴스 1대에서 다른 서비스와 함께 구동되며, 이 서비스가 추가로 쓰는 자원은 메모리 512MB 이내입니다. "
           "추정 운영비는 월 2만~5만원 상당, 정기 점검은 월 2~4시간(데이터 갱신 확인, 기준월 표시 확인, 테스트 실행)입니다. "
           "외부 유료 의존성이 없고 데이터 갱신이 연 1회이므로 유지 부담이 낮습니다. 수상 시 원천 소스와 실행·배포 절차, 데이터 수집 절차, 집계 규칙, 테스트를 함께 인계할 수 있습니다.")

    h(doc, "5-4. 추가 개방이 필요한 공공데이터 의견", 2)
    bullets(doc, [
        "다른 센터(올림픽수영장·분당·올림픽스포츠센터) 강좌정보도 파일 형태로 내려받을 수 있게 개방해 주시면, 센터를 넘나드는 조합까지 계산할 수 있습니다.",
        "강좌별 수강 상태(모집 중·마감)와 잔여석을 공개해 주시면, 신청 가능 여부까지 안내할 수 있습니다.",
        "강습반(수강 대상) 표기를 코드로 표준화해 주시면, 연령 자격을 정확히 판정할 수 있습니다.",
        "시설별 운영 시간표와 휴관일 데이터를 개방해 주시면, 실제 이용 가능한 날짜 기준으로 조합을 제시할 수 있습니다.",
    ])

    doc.save(out)
    print("saved", out)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "detail_proposal.docx"
    figs = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / "Documents/kspo-contest/figs"
    build(out, figs)
