# -*- coding: utf-8 -*-
"""Insert a checklist-evidence index page right after the cover sheet of the
marked PDF: for every applicable 법규 checklist item, show which drawing
number the evidence was found on, or '찾을 수 없음' if it wasn't."""
import json, io, fitz

FONT = r'C:\Windows\Fonts\malgun.ttf'
FONTB = r'C:\Windows\Fonts\malgunbd.ttf'

rows = json.load(io.open(r'D:\DATA\앱개발\drawing-qc\outputs\index_rows.json', encoding='utf-8'))

PDF_IN = r'D:\DATA\앱개발\drawing-qc\outputs\건축도면_marked_v2.pdf'
PDF_OUT = r'D:\DATA\앱개발\drawing-qc\outputs\건축도면_marked_v2_idx.pdf'

doc = fitz.open(PDF_IN)
w, h = doc[0].rect.width, doc[0].rect.height  # display size, e.g. 1191x842

page = doc.new_page(pno=1, width=w, height=h)  # insert right after cover (page index 0)

margin = 30
page.insert_text(fitz.Point(margin, 36), '법규 체크리스트 검토 근거 도면번호 색인',
                  fontsize=15, fontname='malgunbd', fontfile=FONTB, color=(0, 0, 0))
page.insert_text(fitz.Point(margin, 54),
                  '입지관련법규.pdf / 건축물관련법규.pdf 체크리스트 중 도면 대조가 필요한 항목의 근거 위치. '
                  '"대상법규아님" 선언 항목(92건)은 도면 대조 대상이 아니므로 제외.',
                  fontsize=8, fontname='malgun', fontfile=FONT, color=(0.3, 0.3, 0.3))

n = len(rows)
ncols = 2
per_col = (n + ncols - 1) // ncols

col_w = (w - 2 * margin) / ncols
top = 74
row_h = (h - top - margin) / (per_col + 1)
row_h = min(row_h, 12)

COLW = {'no': 22, 'law': col_w * 0.28, 'field': col_w * 0.18, 'result': 42, 'dwgno': col_w * 0.34}
RESULT_LABEL = {'pass': '확인', 'check': '미확인'}
RESULT_COLOR = {'pass': (0, 0.3, 0.9), 'check': (0.85, 0.45, 0)}

for ci in range(ncols):
    x0 = margin + ci * col_w
    y = top
    # header
    hx = x0
    page.insert_text(fitz.Point(hx, y), '#', fontsize=7, fontname='malgunbd', fontfile=FONTB); hx += COLW['no']
    page.insert_text(fitz.Point(hx, y), '법령/체크항목', fontsize=7, fontname='malgunbd', fontfile=FONTB); hx += COLW['law'] + COLW['field']
    page.insert_text(fitz.Point(hx, y), '결과', fontsize=7, fontname='malgunbd', fontfile=FONTB); hx += COLW['result']
    page.insert_text(fitz.Point(hx, y), '근거 도면번호', fontsize=7, fontname='malgunbd', fontfile=FONTB)
    page.draw_line(fitz.Point(x0, y + 3), fitz.Point(x0 + col_w - 8, y + 3), color=(0, 0, 0), width=0.6)
    y += row_h + 2

    chunk = rows[ci * per_col: (ci + 1) * per_col]
    for i, r in enumerate(chunk, start=ci * per_col + 1):
        hx = x0
        page.insert_text(fitz.Point(hx, y), str(i), fontsize=6.3, fontname='malgun', fontfile=FONT)
        hx += COLW['no']

        law_short = r['law']
        if len(law_short) > 20:
            law_short = law_short[:20] + '…'
        page.insert_text(fitz.Point(hx, y), law_short, fontsize=6.3, fontname='malgun', fontfile=FONT)
        field_short = r['field']
        if len(field_short) > 13:
            field_short = field_short[:13] + '…'
        page.insert_text(fitz.Point(hx, y + row_h * 0.5), field_short, fontsize=6.0,
                          fontname='malgun', fontfile=FONT, color=(0.35, 0.35, 0.35))
        hx += COLW['law'] + COLW['field']

        rl = RESULT_LABEL.get(r['result'], r['result'])
        rc = RESULT_COLOR.get(r['result'], (0, 0, 0))
        page.insert_text(fitz.Point(hx, y), rl, fontsize=6.3, fontname='malgun', fontfile=FONT, color=rc)
        hx += COLW['result']

        dwg = r['dwgno']
        is_missing = ('찾을 수 없음' in dwg)
        dcolor = (0.85, 0, 0) if is_missing else (0, 0, 0)
        if len(dwg) > 34:
            dwg = dwg[:34] + '…'
        page.insert_text(fitz.Point(hx, y), dwg, fontsize=6.0, fontname='malgun', fontfile=FONT, color=dcolor)

        y += row_h

doc.save(PDF_OUT, incremental=False)
print('inserted index page, total rows:', n, 'per_col:', per_col)
