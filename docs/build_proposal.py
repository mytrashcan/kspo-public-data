"""기획서 생성기 — 한국체육산업개발(주) 공공데이터 활용 경진대회 제출용 docx.

실행: /usr/local/bin/python3 build_proposal.py <out.docx>
"""
from __future__ import annotations

import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm


def _font(run, size=None, bold=None, color=None, name="맑은 고딕"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def h(doc, text, level=1):
    p = doc.add_heading(level=level)
    run = p.add_run(text)
    _font(run, size=16 if level == 1 else 13, bold=True, color=(0x14, 0x16, 0x1A))
    return p


def para(doc, text, size=10.5, bold=False, space_after=6, indent=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.35
    if indent:
        p.paragraph_format.left_indent = Cm(0.4)
    _font(p.add_run(text), size=size, bold=bold)
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.3
    _font(p.add_run(text), size=size)
    return p


def numbered(doc, text, size=10.5):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.3
    _font(p.add_run(text), size=size)
    return p


def table(doc, rows: list[list[str]], widths_cm: list[float] | None = None, header=True):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j, value in enumerate(row):
            cells[j].text = ""
            p = cells[j].paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(value)
            _font(run, size=9.5, bold=header and i == 0)
            if widths_cm:
                cells[j].width = Cm(widths_cm[j])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def build(path: str) -> None:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "맑은 고딕"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    style.font.size = Pt(10.5)
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)

    # ---------- 표지 ----------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("2026년도 공공데이터 활용 경진대회"), size=13, bold=False, color=(0x7C, 0x81, 0x88))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("기획서"), size=26, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("함께 운동 시간표"), size=18, bold=True, color=(0x13, 0x6F, 0x5A))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run("같이 가서, 각자 운동할 수 있을까요?"), size=11.5, color=(0x45, 0x4B, 0x54))
    doc.add_paragraph()
    table(doc, [
        ["구분", "내용"],
        ["활용사례명", "함께 운동 시간표"],
        ["활용 데이터", "한국체육산업개발주식회사_일산스포츠센터 강좌정보 (data.go.kr 15114776)"],
        ["서비스 주소", "https://kspo.dcselfie.win"],
        ["제출일", "2026년 11월"],
    ], widths_cm=[3.5, 12.0])
    doc.add_page_break()

    # ---------- 기획 요약서 ----------
    h(doc, "기획 요약서", 1)
    para(doc, "1. 활용사례명", bold=True, size=11)
    para(doc, "함께 운동 시간표 — 두 사람이 같은 날 각자 다른 운동을 할 수 있는지 계산하고, 성립하지 않으면 무엇을 얼마나 바꾸면 되는지 제시하는 서비스", indent=True)
    para(doc, "2. 사용한 공공데이터명", bold=True, size=11)
    para(doc, "한국체육산업개발주식회사_일산스포츠센터 강좌정보 (공공데이터포털 15114776, 파일데이터·CSV)", indent=True)
    para(doc, "3. 요약", bold=True, size=11)
    para(doc,
         "두 사람이 각자의 가능한 요일·시간·월 예산을 입력하면, 일산스포츠센터의 실제 강좌 데이터로 같은 요일에 시간이 겹치는 조합과 이어지는 조합을 계산합니다. "
         "조건을 만족하는 조합이 없을 때 단순히 \"없음\"으로 끝내지 않고, 요일 추가·예산 증액·시간 확장·종목 제한 완화 가운데 가장 작은 변경을 실제 강좌로 검증해 제시합니다. "
         "모든 결과에는 강좌번호, 원문 강습반 표기, 데이터 기준월, 원본 CSV 행이 함께 표시됩니다.",
         indent=True)
    para(doc, "4. 기대효과", bold=True, size=11)
    bullet(doc, "동행 운동을 계획할 때 각자 센터 시간표를 따로 확인하고 대조하던 과정을 한 번의 조회로 줄입니다.")
    bullet(doc, "개방된 파일데이터를 계산의 필수 입력으로 사용함으로써, 단순 조회가 아닌 재사용 사례를 만듭니다.")
    bullet(doc, "저수요 강좌가 조건 비교 과정에서 노출되어 센터의 강좌 운영에도 도움이 됩니다.")
    bullet(doc, "데이터의 한계(잔여석 미제공, 대상 구분의 거칢)를 화면에 명시해, 이용자가 센터에 확인해야 할 사항을 분명히 합니다.")
    doc.add_page_break()

    # ---------- 1. 개요 ----------
    h(doc, "1. 활용사례 개요", 1)
    h(doc, "1-1. 활용사례 명", 2)
    para(doc, "함께 운동 시간표", indent=True)
    h(doc, "1-2. 활용사례 기능, 특징 등 세부내용", 2)
    para(doc, "서비스는 네 개의 화면으로 구성됩니다.")
    numbered(doc, "조건 입력: A·B 두 사람의 가능한 요일, 시작·종료 시각, 선호 종목, 제외 종목, 최대 월 회비를 입력합니다.")
    numbered(doc, "결과: 같은 요일에 시간이 겹치는 동시 조합과, 같은 요일에 60분 이내로 이어지는 연속 조합을 합계 월 회비가 낮은 순으로 보여줍니다.")
    numbered(doc, "최소 변경 제안: 조합이 성립하지 않을 때 요일 추가, 예산 증액, 시간창 확장, 종목 제한 완화 중 최소 변경을 제시하고, 그 조합이 실제로 존재하는지 다시 검색해 확인합니다.")
    numbered(doc, "근거: 선택한 두 강좌의 원본 CSV 행 전체, 입력 파일의 SHA-256, 수집 시각, 데이터 기준월을 표시합니다.")
    para(doc, "특징은 다음과 같습니다.", space_after=4)
    bullet(doc, "결과가 항상 원문으로 소급됩니다. 화면의 모든 조합은 강좌번호와 원본 행으로 확인할 수 있습니다.")
    bullet(doc, "실패를 정보로 사용합니다. 조합이 없다는 사실에서 멈추지 않고, 성립에 필요한 최소 조건 변경을 계산합니다.")
    bullet(doc, "데이터 한계를 숨기지 않습니다. 정원은 잔여석이 아니며, 강습반 표기는 원문 그대로 보여주고, 시작일·종료일 필드를 이름만으로 해석하지 않습니다.")

    h(doc, "1-3. 활용사례 서비스 확인 방법", 2)
    para(doc, "로그인 없이 아래 주소에서 바로 확인할 수 있습니다.", space_after=4)
    table(doc, [
        ["확인 항목", "주소"],
        ["서비스 첫 화면", "https://kspo.dcselfie.win"],
        ["결과 화면 예시 (A·B 모두 화·목 18:00–19:00, 월 예산 100,000원·70,000원)",
         "https://kspo.dcselfie.win/plan?a_days=화&a_days=목&a_start=18:00&a_end=19:00&a_budget=100000&b_days=화&b_days=목&b_start=18:00&b_end=19:00&b_budget=70000"],
        ["데이터 근거 화면 예시", "https://kspo.dcselfie.win/evidence?a_code=1029879&b_code=21832"],
        ["데이터 메타데이터 (JSON)", "https://kspo.dcselfie.win/meta"],
    ], widths_cm=[5.5, 10.0])
    para(doc,
         "결과 화면은 조건을 주소에 담고 있어 링크를 그대로 전달하면 같은 결과가 재현됩니다. 별도의 설치나 앱 설치가 필요하지 않습니다.",
         indent=True)

    doc.add_page_break()

    # ---------- 2. 독창성 ----------
    h(doc, "2. 활용사례의 독창성", 1)
    h(doc, "2-1. 활용 공공데이터", 2)
    table(doc, [
        ["데이터셋", "활용 필드", "활용 방식"],
        ["일산스포츠센터 강좌정보 (15114776)",
         "강좌번호, 시작월, 종목, 강좌명, 시작종료시간, 요일, 강습반, 금액, 시작일, 종료일, 링크",
         "요일·시간 겹침 판정, 월 회비 합산, 최소 변경 계산, 원문 표시"],
        ["스포츠센터 강좌 정보 (15147992)",
         "종목, 강좌명, 링크, 등록일, 수정일",
         "강좌 소개·요금 안내 링크 연결(확장 대상)"],
        ["올림픽수영장·분당·올림픽스포츠센터 강좌정보 (15101610·15118652·15110953)",
         "동일 계열 필드",
         "센터 확장을 위한 로더 대상(현재는 일산 단일 센터로 동작)"],
    ], widths_cm=[5.0, 5.5, 5.0])
    para(doc,
         "계산의 입력 자체가 공공데이터입니다. 다른 데이터를 곁들인 부가 기능이 아니라, 강좌의 요일·시간·요금이 없으면 서비스가 성립하지 않습니다.",
         indent=True)

    h(doc, "2-2. 사례를 활용하게 된 배경 및 활용 우수성", 2)
    para(doc, "[배경]", bold=True, space_after=3)
    para(doc,
         "공모전이 제시한 예시는 공연 알림, 혼잡도 예측·분산 안내, 실감형 콘텐츠 세 가지이며, 주최기관은 공연 일정과 예상 주차장 이용률을 안내하는 자체 서비스를 이미 운영하고 있습니다. "
         "같은 축에서 새 서비스를 만들면 기존 서비스와 비교되어 차별성이 드러나기 어렵습니다. 그래서 시설 운영 데이터 가운데 아직 화면으로 소비되지 않은 영역인 "
         "\"강좌 시간표\"를 골랐습니다. 시간표는 시설의 하루를 그대로 담고 있지만, 지금까지는 사람이 눈으로 대조해야 하는 정보였습니다.",
         indent=True)
    para(doc, "[활용 우수성 — 실측 근거]", bold=True, space_after=3)
    table(doc, [
        ["측정 항목", "실측값"],
        ["입력 파일 규모", "17,146행 (CP949, 2.9MB), 유효 파싱 17,073행"],
        ["분석 대상 강좌", "최신 강좌월 2026-10 기준 155개, 15종목"],
        ["월 회비 범위", "21,000원 ~ 160,000원"],
        ["같은 요일·같은 시간대에 서로 다른 종목이 있는 슬롯", "22개 (예: 화·목 18:00–18:50에 농구·TRX·기구필라테스)"],
        ["동시 조합으로 계산된 쌍", "468쌍"],
        ["같은 날 60분 이내 연속 조합", "602쌍"],
    ], widths_cm=[9.0, 6.5])
    para(doc, "[차별점]", bold=True, space_after=3)
    numbered(doc, "결과를 원문까지 소급합니다. 화면의 조합은 강좌번호와 원본 CSV 행, 파일 해시, 수집 시각으로 확인됩니다.")
    numbered(doc, "성립하지 않는 조건을 정보로 바꿉니다. 요일 1개 추가, 예산 5,000원 증액처럼 최소 변경과 그 비용을 계산하고, 제안한 변경으로 다시 검색해 실제 조합이 존재하는지 검증한 뒤에만 화면에 표시합니다.")
    numbered(doc, "데이터의 함정을 화면에 명시합니다. 정원을 잔여석으로 해석하지 않고, 시작일 필드에 섞여 있는 기간 문자열을 무시하며, 강습반 표기는 원문 그대로 보여줍니다. 이는 심사기관이 데이터를 가장 잘 아는 주체라는 점을 고려한 설계입니다.")
    numbered(doc, "예측하지 않습니다. 관측하지 않은 값(대기시간·만차 여부·수강 가능 여부)을 추정해 표시하지 않으므로, 결과의 신뢰 범위가 명확합니다.")

    doc.add_page_break()

    # ---------- 3. 구체성 ----------
    h(doc, "3. 활용사례의 구체성", 1)
    para(doc, "[처리 흐름]", bold=True, space_after=3)
    table(doc, [
        ["단계", "내용"],
        ["수집", "공공데이터포털에서 강좌정보 CSV를 내려받아 파일 해시와 함께 고정"],
        ["정규화", "시작월·요일·시작/종료 시각·월 회비·강습반·원문 행을 타입이 있는 레코드로 변환. 누락 사유별 탈락 건수 기록"],
        ["저장", "SQLite에 최신 강좌월만 적재하고, 데이터셋 ID·파일명·해시·유효행수·기준월·수집시각을 메타로 함께 보관"],
        ["계산", "두 사람의 조건을 만족하는 강좌를 추린 뒤 조합 탐색. 동시 조합은 겹침 시간, 연속 조합은 간격으로 분류"],
        ["조건 완화", "성립 조합이 없을 때 실제 조합을 기준으로 요일·예산·시간·종목 변경량을 역산하고, 변경된 조건으로 다시 검색해 검증"],
        ["표시", "결과 카드, 최소 변경 제안, 원문 근거 화면"],
    ], widths_cm=[3.0, 12.5])
    para(doc, "[조합 판정 규칙]", bold=True, space_after=3)
    bullet(doc, "강좌에 적힌 모든 요일과 수업 시간이 각자의 조건 안에 들어와야 후보가 됩니다.")
    bullet(doc, "두 강좌의 공통 요일이 있어야 하며, 서로 다른 강좌·같은 센터·같은 강좌월이어야 합니다.")
    bullet(doc, "시간이 겹치면 동시 조합, 겹치지 않고 60분 이내로 이어지면 연속 조합으로 분류합니다.")
    bullet(doc, "정렬은 합계 월 회비 오름차순, 다음으로 겹침이 긴 순서입니다.")
    para(doc, "[최소 변경 계산]", bold=True, space_after=3)
    bullet(doc, "요일: 두 사람이 허용하지 않은 요일 중 실제 강좌가 쓰는 요일의 개수")
    bullet(doc, "예산: 각자 예산 상한 대비 실제 월 회비 초과분의 합")
    bullet(doc, "시간: 시작 시각을 앞당겨야 하는 분, 종료 시각을 늦춰야 하는 분의 합")
    bullet(doc, "종목: 선호·제외 조건과 실제 강좌가 어긋난 인원 수")
    bullet(doc, "유형별로 가장 작은 변경을 하나씩 제시하고, 한 유형만으로 성립하지 않으면 여러 변경을 함께 제시합니다. 모든 제안은 변경된 조건으로 재검색해 실제 조합이 확인된 경우에만 노출됩니다.")
    para(doc, "[검증]", bold=True, space_after=3)
    bullet(doc, "자동 테스트 80건: 파서 함정(기간 문자열, 빈 값, 인코딩), 요일·시간 파싱, 조합 3분기(동시·연속·성립 불가), 최소 변경 4유형, 화면·API 응답, 금지 문구 가드")
    bullet(doc, "금지 문구 가드: 화면에 '잔여석·신청 가능·대기시간'이 등장하면 테스트가 실패하도록 고정했습니다(면책 문구 1곳 예외).")
    bullet(doc, "실행 예시: A(TRX 18시, 월 100,000원) + B(농구 18시, 월 35,000원) = 합계 월 135,000원, 겹치는 시간 50분. 두 강좌 모두 강좌번호와 원본 행으로 확인됩니다.")

    doc.add_page_break()

    # ---------- 4. 활용 적절성 ----------
    h(doc, "4. 사례의 활용 적절성", 1)
    para(doc, "[사회적 가치]", bold=True, space_after=3)
    bullet(doc, "동행 부담 완화: 부모와 자녀, 부부, 친구가 같은 시간에 각자 운동하려면 두 사람의 시간표를 각자 확인해 대조해야 합니다. 이 과정을 한 번의 조회로 줄입니다.")
    bullet(doc, "운동 참여 장벽 완화: \"함께 갈 수 있는 시간이 없다\"는 판단을, \"무엇을 바꾸면 가능한가\"라는 판단으로 바꿉니다.")
    bullet(doc, "센터 운영 지원: 상담 창구에서 반복되는 시간표 문의를 줄이고, 조건 비교 과정에서 평소 노출되지 않던 강좌가 드러납니다.")
    bullet(doc, "공공데이터 활용 촉진: 조회·목록 소비에 머물던 시설 파일데이터를 계산의 입력으로 사용하는 사례를 만듭니다.")
    para(doc, "[한계와 정직한 범위]", bold=True, space_after=3)
    para(doc,
         "이 서비스는 수강 신청을 대신하지 않습니다. 공개 데이터에 잔여석과 수강 상태가 없으므로 신청 가능 여부를 판단하지 않으며, 화면에도 그 사실을 명시합니다. "
         "또한 강습반 표기가 거칠어(155개 중 115개가 '성인남여및청소년') 연령 자격을 자동 판정하지 않고 원문을 그대로 보여줍니다. "
         "따라서 이용자는 후보를 좁힌 뒤 센터에 확인하는 절차를 거치게 되며, 이 확인 절차를 없애는 것을 목표로 삼지 않습니다.",
         indent=True)

    # ---------- 5. 실현가능성 ----------
    h(doc, "5. 실현가능성 및 기타", 1)
    para(doc, "[추진 일정]", bold=True, space_after=3)
    table(doc, [
        ["기간", "내용", "상태"],
        ["2026-11-06", "데이터 접근성·신선도 검증(강좌 155개, 최신 기준월 2026-10), 조합 계산 가능성 확인", "완료"],
        ["2026-11-06", "수집·정규화·조합 엔진·근거 화면 구현, 자동 테스트 80건", "완료"],
        ["2026-11-06", "공개 주소 배포(HTTPS), 데모 링크 재현 확인", "완료"],
        ["2026-11 중순", "다른 센터 강좌 데이터 확장, 사용성 검토 반영", "예정"],
        ["2026-11 말", "기능 동결, 시연 영상·제출 서류 마무리", "예정"],
        ["2026-12-01", "접수 마감(이메일 제출)", "예정"],
    ], widths_cm=[3.2, 10.3, 2.0])
    para(doc, "[개발·운영 계획]", bold=True, space_after=3)
    bullet(doc, "구성: Python 3.12, FastAPI, SQLite, 서버 렌더링 화면. 외부 유료 API·문자 발송·LLM 호출이 없어 운영 비용이 고정적입니다.")
    bullet(doc, "데이터 갱신: 강좌정보는 연간 갱신 주기이므로, 갱신된 파일을 받아 해시와 기준월을 갱신하고 재적재합니다. 갱신 파일이 없으면 마지막 정상 데이터를 유지하되 기준월을 함께 표시합니다.")
    bullet(doc, "장애 대응: 데이터 적재 실패·스키마 변경 시 이전 적재본으로 동작하고, 화면 상단의 기준월로 상태를 알 수 있습니다.")
    bullet(doc, "인수 가능성: 실행 방법, 데이터 수집 절차, 집계·계산 규칙, 테스트, 의존성 목록을 저장소 문서로 함께 제공합니다.")
    para(doc, "[2028년까지 운영 가능 여부]", bold=True, space_after=3)
    para(doc,
         "가능합니다. 현재 소규모 클라우드 인스턴스 1대에서 다른 서비스와 함께 구동되며, 이 서비스가 추가로 쓰는 자원은 메모리 512MB 이내입니다. "
         "추정 운영비는 월 2만~5만원 상당, 정기 점검은 월 2~4시간(데이터 갱신 확인, 기준월 표시 확인, 테스트 실행)입니다. "
         "외부 유료 의존성이 없고 데이터 갱신이 연 1회이므로, 유지 부담이 낮은 구조입니다.",
         indent=True)
    para(doc, "[추가 개방이 필요한 공공데이터 의견]", bold=True, space_after=3)
    bullet(doc, "다른 센터(올림픽수영장·분당·올림픽스포츠센터) 강좌정보도 파일 형태로 내려받을 수 있게 개방해 주시면, 센터를 넘나드는 조합까지 계산할 수 있습니다.")
    bullet(doc, "강좌별 수강 상태(모집 중·마감)와 잔여석을 공개해 주시면, 신청 가능 여부까지 안내할 수 있습니다.")
    bullet(doc, "강습반(수강 대상) 표기를 코드로 표준화해 주시면, 연령 자격을 정확히 판정할 수 있습니다.")
    bullet(doc, "시설별 운영 시간표와 휴관일 데이터를 개방해 주시면, 실제 이용 가능한 날짜 기준으로 조합을 제시할 수 있습니다.")

    doc.save(path)
    print(f"saved {path}")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "proposal.docx")
