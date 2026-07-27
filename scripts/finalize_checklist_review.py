# -*- coding: utf-8 -*-
"""Compile the final per-item checklist review: for every applicable item,
pick representative drawing-number evidence (or mark not found)."""
import json, io, sys
sys.path.insert(0, r'D:\DATA\앱개발\drawing-qc\scripts')
import search_evidence as se

items = json.load(io.open(r'D:\DATA\앱개발\drawing-qc\outputs\checklist_items.json', encoding='utf-8'))
evidence = json.load(io.open(r'D:\DATA\앱개발\drawing-qc\outputs\evidence_search.json', encoding='utf-8'))

# refined keyword overrides discovered during manual review (better recall than the first pass)
OVERRIDES = {
    7: ['건축한계선'],
    8: ['건축한계선'],
    15: ['건축한계선', '대지경계선'],
}
NOT_APPLICABLE_ON_DRAWING = {
    # items that are inherently administrative/paperwork or belong to a
    # non-architectural (MEP/civil) drawing set outside this PDF's scope
    1, 2, 21, 24, 31, 32, 33, 36, 37, 38, 40, 49, 50, 52, 53, 55, 56, 57, 59, 60, 61,
}

need = [it for it in items if '대상법규아님' not in it['selected']]

results = []
for i, it in enumerate(need):
    kws = OVERRIDES.get(i, evidence[str(i)]['keywords'])
    hits = se.search(kws) if kws else {}
    pages = sorted(hits.keys())
    entry = {
        'idx': i,
        'source': it['source'], 'no': it['no'], 'law': it['law'], 'field': it['field'],
        'selected': it['selected'], 'keywords': kws,
    }
    if pages:
        primary = pages[0]
        w0 = hits[primary][0]
        entry['found'] = True
        entry['dwgno_list'] = [se.dwgno(p) for p in pages]
        entry['primary_page'] = primary
        entry['primary_dwgno'] = se.dwgno(primary)
        entry['primary_x'] = w0['x']
        entry['primary_y'] = w0['y']
        entry['n_pages'] = len(pages)
        entry['sample'] = sorted(set(w['text'] for w in hits[primary]))[:5]
    else:
        entry['found'] = False
        entry['not_on_drawing_scope'] = i in NOT_APPLICABLE_ON_DRAWING
    results.append(entry)

json.dump(results, io.open(r'D:\DATA\앱개발\drawing-qc\outputs\checklist_final.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

found = sum(1 for r in results if r['found'])
print(f'total {len(results)}, found {found}, not found {len(results)-found}')
