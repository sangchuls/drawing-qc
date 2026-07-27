# -*- coding: utf-8 -*-
"""Build the two deliverables:
 1) outputs/checklist_review.xlsx  - every checklist row with 도면번호 evidence
 2) outputs/results.json (rebuilt) - marking entries for mark.py, now with
    genuine page/x/y evidence (or a 'not found' page-1 flag) for every
    applicable item, replacing the old lazy page=1/x=50/y=50 defaults.
"""
import json, io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

items = json.load(io.open(r'D:\DATA\앱개발\drawing-qc\outputs\checklist_items.json', encoding='utf-8'))
final = json.load(io.open(r'D:\DATA\앱개발\drawing-qc\outputs\checklist_final.json', encoding='utf-8'))
final_by_key = {(f['source'], f['no'], f['field']): f for f in final}

NEG_PREFIXES = ('비대상', '해당없음', '검토제외')

def polarity(selected):
    if not selected:
        return 'unknown'
    return 'negative' if selected[0].startswith(NEG_PREFIXES) else 'positive'

rows = []  # for excel
mark_entries = []  # for results.json / mark.py

for it in items:
    key = (it['source'], it['no'], it['field'])
    na = '대상법규아님' in it['selected']
    row = {
        'source': it['source'], 'no': it['no'], 'law': it['law'], 'field': it['field'],
        'selected': ', '.join(it['selected']),
    }
    if na:
        row['status'] = '해당없음(대상법규아님)'
        row['dwgno'] = '-'
        row['result'] = 'n/a'
        row['comment'] = '체크리스트 원본에서 대상법규아님으로 선언되어 도면 대조 대상 아님.'
        rows.append(row)
        continue

    f = final_by_key.get(key)
    if f is None:
        row['status'] = '찾을 수 없음'
        row['dwgno'] = '찾을 수 없음'
        row['result'] = 'check'
        row['comment'] = '체크리스트 파싱 매칭 실패(수동 확인 필요).'
        rows.append(row)
        continue

    pol = polarity(it['selected'])

    if f['found']:
        dwgno_display = ', '.join(sorted(set(f['dwgno_list']))[:6])
        if len(set(f['dwgno_list'])) > 6:
            dwgno_display += f" 외 {len(set(f['dwgno_list']))-6}건"
        sample = ', '.join(f['sample'])
        if pol == 'negative':
            row['status'] = f"관련 표기 발견({dwgno_display}) - 선언값과 명칭이 다를 수 있어 육안 재확인 권장"
            row['result'] = 'check'
            comment = (f"검색어 '{'/'.join(f['keywords'])}' 관련 표기가 {f['primary_dwgno']}({f['primary_page']}p) 등에서 "
                       f"확인됨(예: {sample}). 체크리스트상 '{it['selected'][0]}' 선언과 다른 문맥일 수 있어 "
                       f"실제 도면 확인 권장.")
        else:
            row['status'] = f"확인됨 - {dwgno_display}"
            row['result'] = 'pass'
            comment = (f"{f['primary_dwgno']}({f['primary_page']}p) 등 {f['n_pages']}개 시트에서 "
                       f"'{sample}' 등 관련 표기 확인 - '{it['selected'][0]}' 선언과 부합.")
        row['dwgno'] = dwgno_display
        row['comment'] = comment
        mark_entries.append({
            'category': '법규', 'item': f"{it['law']} - {it['field']}({', '.join(it['selected'])})",
            'result': row['result'], 'color': 'red' if row['result'] == 'error' else 'blue',
            'page': f['primary_page'], 'x': f['primary_x'], 'y': f['primary_y'],
            'comment': comment, 'located': True,
        })
    else:
        if pol == 'negative':
            row['status'] = '표기 없음(선언과 부합)'
            row['dwgno'] = '해당 표기 없음(비대상과 일치)'
            row['result'] = 'pass'
            comment = (f"85페이지 전체에서 '{'/'.join(f['keywords'])}' 관련 표기가 확인되지 않음 - "
                       f"'{it['selected'][0]}' 선언과 모순되지 않음.")
        else:
            scope_note = ''
            if f.get('not_on_drawing_scope'):
                scope_note = ' (서류/타 분야 도면(설비·구조 등) 확인 사항으로 추정)'
            row['status'] = '찾을 수 없음'
            row['dwgno'] = '찾을 수 없음'
            row['result'] = 'check'
            comment = (f"건축도면 85페이지 전체를 '{'/'.join(f['keywords'])}' 키워드로 검색했으나 "
                       f"관련 표기를 찾을 수 없음{scope_note}. 서류 또는 별도 도면 확인 필요.")
        row['comment'] = comment
        mark_entries.append({
            'category': '법규', 'item': f"{it['law']} - {it['field']}({', '.join(it['selected'])})",
            'result': row['result'], 'color': 'blue',
            'page': 1, 'x': 50, 'y': 50,
            'comment': comment, 'located': False,
        })
    rows.append(row)

# ---- Excel output ----
wb = openpyxl.Workbook()
ws = wb.active
ws.title = '법규체크리스트_검토결과'
headers = ['구분', '번호', '법령', '체크항목', '체크리스트 선언값', '검토결과', '근거 도면번호', '비고']
ws.append(headers)
for c in ws[1]:
    c.font = Font(bold=True, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor='2F5496')
    c.alignment = Alignment(wrap_text=True, vertical='center')

RESULT_FILL = {
    'pass': PatternFill('solid', fgColor='DDEBF7'),
    'check': PatternFill('solid', fgColor='FFF2CC'),
    'error': PatternFill('solid', fgColor='FCE4E4'),
    'n/a': PatternFill('solid', fgColor='F2F2F2'),
}

for row in rows:
    ws.append([row['source'], row['no'], row['law'], row['field'], row['selected'],
               row['result'], row['dwgno'], row['comment']])
    fill = RESULT_FILL.get(row['result'])
    if fill:
        ws.cell(row=ws.max_row, column=6).fill = fill

widths = [12, 6, 34, 22, 16, 10, 28, 55]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
ws.freeze_panes = 'A2'

wb.save(r'D:\DATA\앱개발\drawing-qc\outputs\checklist_review.xlsx')

json.dump(mark_entries, io.open(r'D:\DATA\앱개발\drawing-qc\outputs\results_law.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

# compact rows for the marked-PDF index page (only rows that needed a drawing check)
index_rows = [
    {'source': r['source'], 'no': r['no'], 'law': r['law'], 'field': r['field'],
     'result': r['result'], 'dwgno': r['dwgno']}
    for r in rows if r['result'] != 'n/a'
]
json.dump(index_rows, io.open(r'D:\DATA\앱개발\drawing-qc\outputs\index_rows.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

found_pos = sum(1 for r in rows if r['result'] == 'pass')
check_n = sum(1 for r in rows if r['result'] == 'check')
na_n = sum(1 for r in rows if r['result'] == 'n/a')
print(f'rows total={len(rows)} pass={found_pos} check={check_n} n/a={na_n}')
print('saved outputs/checklist_review.xlsx and outputs/results_law.json')
