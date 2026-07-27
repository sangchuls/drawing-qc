"""Builds the two review deliverables: an index page inserted into the
marked PDF, and an Excel checklist report — ported from the original
session's scripts/insert_index_page.py and scripts/build_final_outputs.py.
"""
import os

import fitz
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from .mark import FONT, FONT_BOLD

RESULT_LABEL = {"pass": "확인", "check": "미확인", "error": "오류", "n/a": "해당없음"}
RESULT_COLOR = {"pass": (0, 0.3, 0.9), "check": (0.85, 0.45, 0), "error": (0.85, 0, 0)}
RESULT_FILL = {
    "pass": PatternFill("solid", fgColor="DDEBF7"),
    "check": PatternFill("solid", fgColor="FFF2CC"),
    "error": PatternFill("solid", fgColor="FCE4E4"),
    "n/a": PatternFill("solid", fgColor="F2F2F2"),
}


def dwgno_display(row: dict) -> str:
    if row["result"] == "n/a":
        return "-"
    dwgs = sorted(set(row.get("dwgno_list") or []))
    if not dwgs:
        return "찾을 수 없음"
    text = ", ".join(dwgs[:6])
    if len(dwgs) > 6:
        text += f" 외 {len(dwgs) - 6}건"
    return text


def insert_index_page(pdf_in: str, rows: list[dict], pdf_out: str):
    applicable = [r for r in rows if r["result"] != "n/a"]

    doc = fitz.open(pdf_in)
    w, h = doc[0].rect.width, doc[0].rect.height
    page = doc.new_page(pno=min(1, doc.page_count), width=w, height=h)

    margin = 30
    page.insert_text(fitz.Point(margin, 36), "체크리스트 검토 근거 도면번호 색인",
                      fontsize=15, fontname="dqcfontb", fontfile=FONT_BOLD, color=(0, 0, 0))
    page.insert_text(fitz.Point(margin, 54),
                      f"도면 대조가 필요한 항목 {len(applicable)}건. "
                      f"'해당없음' 처리된 항목은 체크리스트에서 비적용으로 선언되어 제외됨.",
                      fontsize=8, fontname="dqcfont", fontfile=FONT, color=(0.3, 0.3, 0.3))

    n = len(applicable)
    if n == 0:
        doc.save(pdf_out)
        return

    ncols = 2 if n > 30 else 1
    per_col = (n + ncols - 1) // ncols
    col_w = (w - 2 * margin) / ncols
    top = 74
    row_h = min((h - top - margin) / (per_col + 1), 12)

    colw = {"no": 22, "law": col_w * 0.28, "field": col_w * 0.18, "result": 42, "dwgno": col_w * 0.34}

    for ci in range(ncols):
        x0 = margin + ci * col_w
        y = top
        hx = x0
        page.insert_text(fitz.Point(hx, y), "#", fontsize=7, fontname="dqcfontb", fontfile=FONT_BOLD)
        hx += colw["no"]
        page.insert_text(fitz.Point(hx, y), "법령/체크항목", fontsize=7, fontname="dqcfontb", fontfile=FONT_BOLD)
        hx += colw["law"] + colw["field"]
        page.insert_text(fitz.Point(hx, y), "결과", fontsize=7, fontname="dqcfontb", fontfile=FONT_BOLD)
        hx += colw["result"]
        page.insert_text(fitz.Point(hx, y), "근거 도면번호", fontsize=7, fontname="dqcfontb", fontfile=FONT_BOLD)
        page.draw_line(fitz.Point(x0, y + 3), fitz.Point(x0 + col_w - 8, y + 3), color=(0, 0, 0), width=0.6)
        y += row_h + 2

        chunk = applicable[ci * per_col:(ci + 1) * per_col]
        for i, r in enumerate(chunk, start=ci * per_col + 1):
            hx = x0
            page.insert_text(fitz.Point(hx, y), str(i), fontsize=6.3, fontname="dqcfont", fontfile=FONT)
            hx += colw["no"]

            law_short = r["law"][:20] + ("…" if len(r["law"]) > 20 else "")
            page.insert_text(fitz.Point(hx, y), law_short, fontsize=6.3, fontname="dqcfont", fontfile=FONT)
            field_short = r["field"][:13] + ("…" if len(r["field"]) > 13 else "")
            page.insert_text(fitz.Point(hx, y + row_h * 0.5), field_short, fontsize=6.0,
                              fontname="dqcfont", fontfile=FONT, color=(0.35, 0.35, 0.35))
            hx += colw["law"] + colw["field"]

            rl = RESULT_LABEL.get(r["result"], r["result"])
            rc = RESULT_COLOR.get(r["result"], (0, 0, 0))
            page.insert_text(fitz.Point(hx, y), rl, fontsize=6.3, fontname="dqcfont", fontfile=FONT, color=rc)
            hx += colw["result"]

            dwg = dwgno_display(r)
            is_missing = dwg == "찾을 수 없음"
            dwg_short = dwg[:34] + ("…" if len(dwg) > 34 else "")
            page.insert_text(fitz.Point(hx, y), dwg_short, fontsize=6.0, fontname="dqcfont", fontfile=FONT,
                              color=(0.85, 0, 0) if is_missing else (0, 0, 0))
            y += row_h

    doc.save(pdf_out)


def build_excel(rows: list[dict], xlsx_out: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "체크리스트_검토결과"
    headers = ["구분", "법령/항목", "체크항목", "체크리스트 선언값", "검토결과", "근거 도면번호", "코멘트"]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2F5496")
        c.alignment = Alignment(wrap_text=True, vertical="center")

    for r in rows:
        ws.append([
            r["source"], r["law"], r["field"], ", ".join(r.get("selected") or []),
            r["result"], dwgno_display(r), r.get("comment", ""),
        ])
        fill = RESULT_FILL.get(r["result"])
        if fill:
            ws.cell(row=ws.max_row, column=5).fill = fill

    widths = [16, 34, 22, 16, 10, 28, 55]
    for i, wd in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = wd
    ws.freeze_panes = "A2"
    wb.save(xlsx_out)


def summary_rows_for_web(rows: list[dict]) -> list[dict]:
    return [
        {"source": r["source"], "law": r["law"], "field": r["field"],
         "result": r["result"], "dwgno": dwgno_display(r)}
        for r in rows
    ]
