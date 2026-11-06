"""참가신청서·개인정보 동의서 작업본 생성 (2026년도 공공데이터 활용 경진대회).

공식 양식(안내문 붙임1, 붙임1-1)의 항목과 문구를 그대로 옮기고,
활용사례 관련 항목만 채워 둔 작업본을 만든다. 개인정보는 빈칸으로 남긴다.

실행: /usr/local/bin/python3 build_forms.py <out.docx>
"""
from __future__ import annotations

import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FILL = (0x9A, 0x30, 0x0F)  # 채워야 할 칸 표시색


def _font(run, size=10.5, bold=False, color=None):
    run.font.name = "맑은 고딕"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def para(doc, text="", size=10.5, bold=False, color=None, align=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.3
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if text:
        _font(p.add_run(text), size=size, bold=bold, color=color)
    return p


def cell(c, text, size=9.5, bold=False, color=None, align_center=False, width=None):
    c.text = ""
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(1)
    if align_center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run(text), size=size, bold=bold, color=color)
    if width:
        c.width = Cm(width)


def table(doc, rows, widths=None, header=False):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j, value in enumerate(row):
            if isinstance(value, tuple):
                text, color = value
                cell(cells[j], text, color=color, bold=(header and i == 0))
            else:
                cell(cells[j], value, bold=(header and i == 0))
            if widths:
                cells[j].width = Cm(widths[j])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def build(path: str) -> None:
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

    para(doc, "2026년도 공공데이터 활용 경진대회 참가 신청서", size=15, bold=True, align="center", space_after=2)
    para(doc, "※ 주황색 글씨는 이미 채운 항목, 빨간 밑줄 칸은 신청인이 직접 채울 항목입니다.", size=9, color=(0x6B, 0x6B, 0x6B), align="center", space_after=10)

    rows = [
        ["참가구분", ("□ 개인    □ 팀", FILL)],
        ["참가분야", "□ 활용 사례"],
        ["성명(대표자)  * 팀 참가 시 팀장명", ("", FILL)],
        ["생년월일", ("YYYY-MM-DD", FILL)],
        ["휴대전화번호", ("", FILL)],
        ["이메일", ("", FILL)],
        ["주소", ("", FILL)],
        ["소속(기업)", ("", FILL)],
        ["팀명", ("", FILL)],
    ]
    table(doc, rows, widths=[5.6, 11.4])

    para(doc, "팀원 (팀 참가 시에만 기재 · 팀장 포함 5인 이내)", size=10, bold=True, space_after=3)
    table(doc, [
        ["구분", "성명", "휴대전화번호", "이메일"],
        ["팀원1", ("", FILL), ("", FILL), ("", FILL)],
        ["팀원2", ("", FILL), ("", FILL), ("", FILL)],
        ["팀원3", ("", FILL), ("", FILL), ("", FILL)],
        ["팀원4", ("", FILL), ("", FILL), ("", FILL)],
    ], widths=[2.6, 3.6, 4.0, 5.0])

    para(doc, "활용사례", size=10, bold=True, space_after=3)
    table(doc, [
        ["활용사례 제목", ("함께 운동 시간표", FILL)],
        ["활용데이터", ("한국체육산업개발주식회사_일산스포츠센터 강좌정보(data.go.kr 15114776)", FILL)],
        ["활용사례 기획 개요",
         ("두 사람의 요일·시간·월 예산을 입력하면 일산스포츠센터 실제 강좌로 같은 날 함께 갈 수 있는 조합을 계산합니다. "
          "조건이 성립하지 않으면 요일·예산·시간·종목 중 가장 작은 변경을 실제 강좌로 검증해 제시합니다.", FILL)],
    ], widths=[3.6, 13.4])

    doc.add_page_break()

    para(doc, "참가 서약서", size=13, bold=True, align="center", space_after=8)
    para(doc, "본인은 한국체육산업개발(주)에서 개최하는 「2026년도 공공데이터 활용 경진대회」에 참가하면서, 다음 각 호의 규정을 지킬 것을 서약합니다.", space_after=6)
    for line in [
        "1. 대회의 제반 규정을 준수하겠습니다.",
        "2. 참가신청서 및 기획서에 기재한 내용이 사실임을 확인하며, 허위 사실 기재 등으로 인하여 문제가 발생하면 모든 책임은 본인(팀)에게 있음을 확인합니다.",
        "3. 응모작에 대한 저작권으로 인하여 발생하는 민·형사상 책임은 참가자에게 있습니다.",
        "4. 동일·유사 응모작으로 타 경진대회에서 수상한 사실이 있거나, 타인의 저작권을 침해하거나, 제출 내용이 허위로 확인되는 경우 접수 및 수상이 취소될 수 있으며, 이미 지급 받은 시상금은 반환합니다.",
        "5. 응모작의 저작권은 참가자에게 귀속되며, 수상작에 한하여 한국체육산업개발(주)가 정책개선 및 공공 활용을 위하여 홈페이지 등에 게재·공개하는 것에 동의합니다.",
        "6. 수상작의 경우 웹/앱 등 원천 개발 소스 제공 및 2028년까지 서비스 운영에 협조하겠습니다.",
        "7. 심사 결과에 대해 이의를 제기하지 않으며, 원활한 대회 진행에 적극적으로 협조하겠습니다.",
    ]:
        para(doc, line, space_after=3)

    para(doc, "", space_after=10)
    para(doc, "2026년      월      일", align="center", space_after=6)
    para(doc, "신청인                    (인)", align="center", space_after=6)
    para(doc, "한국체육산업개발주식회사 귀하", align="center", space_after=4)
    para(doc, "※ 자필 서명 후 스캔하거나, 서명 이미지를 넣어 제출하세요.", size=9, color=(0x6B, 0x6B, 0x6B), align="center")

    doc.add_page_break()

    para(doc, "개인정보 수집 및 이용에 관한 동의서", size=13, bold=True, align="center", space_after=8)
    para(doc, "1. 개인정보 수집‧이용 목적", bold=True, space_after=2)
    para(doc, "「2026년도 공공데이터 활용 경진대회」 참가자 관리, 수상자 선정, 진행 상황 안내, 수상작 활용 협약 체결 및 사후 관리를 위해 개인정보를 수집하며, 목적 이외의 용도로는 사용하지 않습니다.")
    para(doc, "2. 개인정보 처리자", bold=True, space_after=2)
    para(doc, "한국체육산업개발(주) 디지털혁신팀 02-2180-3504")
    para(doc, "3. 개인정보 수집‧이용 항목", bold=True, space_after=2)
    para(doc, "이름, 생년월일, 휴대전화번호, 이메일, 주소, 소속, 팀명")
    para(doc, "※ 수상자의 시상금 지급을 위한 정보는 수상 확정 후 별도 동의를 받아 수집", space_after=6)
    para(doc, "4. 동의 거부 권리 및 불이익", bold=True, space_after=2)
    para(doc, "신청자는 개인정보 수집·이용 동의에 대해 거부할 권리가 있습니다. 다만, 동의를 거부할 경우에는 「2026년도 공공데이터 활용 경진대회」 참가자에 대한 공정한 심사 등을 위해 참가가 제한됩니다.")
    para(doc, "5. 보유 및 이용기간", bold=True, space_after=2)
    para(doc, "일반참가자는 결과 발표 후 즉시 해당 정보 파기, 수상자의 경우 시상금 지급 완료 및 수상작 서비스 운영 협약 종료일(2028년)까지 보유합니다.")
    para(doc, "관련 법령에 따라 보존이 필요한 정보는 해당 기간 동안 보존하며, 보유기간 경과 시 지체 없이 파기합니다.")
    para(doc, "본인은 개인정보 수집‧이용에 관한 상기 내용을 확인하였으며, 아래와 같이 동의합니다.", space_after=8)

    para(doc, "2026 년     월     일", align="center", space_after=6)
    table(doc, [
        ["동의 여부", "이름", "서명"],
        [("□ 동의  /  □ 거부", FILL), ("", FILL), ("", FILL)],
        [("□ 동의  /  □ 거부", FILL), ("", FILL), ("", FILL)],
        [("□ 동의  /  □ 거부", FILL), ("", FILL), ("", FILL)],
        [("□ 동의  /  □ 거부", FILL), ("", FILL), ("", FILL)],
        [("□ 동의  /  □ 거부", FILL), ("", FILL), ("", FILL)],
    ], widths=[6.0, 5.0, 6.0], header=True)

    doc.save(path)
    print("saved", path)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "forms.docx")
