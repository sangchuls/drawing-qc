# -*- coding: utf-8 -*-
import json, io, sys
sys.path.insert(0, r'D:\DATA\앱개발\drawing-qc\scripts')
import search_evidence as se

# (needs_check index, keywords) — curated per item based on the checklist field/law text
QUERIES = {
 0:  ['설계자'],
 1:  ['설계도서'],
 2:  ['서명', '날인'],
 3:  ['조경'],
 4:  ['공개공지'],
 5:  ['접도', '도로'],
 6:  ['접도', '도로'],
 7:  ['건축선'],
 8:  ['건축선'],
 9:  ['피난', '방화구획', '비상구', '피난층'],
 10: ['내화구조', '내화'],
 11: ['방화벽'],
 12: ['불연재', '준불연', '난연', '마감재료'],
 13: ['지하층'],
 14: ['거실'],
 15: ['대지안', '공지'],
 16: ['가로구역'],
 17: ['건축설비'],
 18: ['승강기', 'ELEV'],
 19: ['비상용'],
 20: ['피난용승강기', '피난용 승강기'],
 21: ['내진'],
 22: ['면적', '층수'],
 23: ['구조', '내력'],
 24: ['내진'],
 25: ['EL+', 'GL'],
 26: ['옹벽', '경사'],
 27: ['오수', '집수정'],
 28: ['장애인', '점자'],
 29: ['에너지절약', '에너지 절약'],
 30: ['에너지절약'],
 31: ['녹색건축'],
 32: ['완화'],
 33: ['미술작품'],
 34: ['소방', '소화전'],
 35: ['소방시설', '스프링클러', '소화전'],
 36: ['절수'],
 37: ['급수', '수도'],
 38: ['저수조'],
 39: ['위험물', '유류저장', '발전기'],
 40: ['위험물'],
 41: ['자전거'],
 42: ['장애인주차', '장애인 전용'],
 43: ['통신', 'TPS', '전기통신'],
 44: ['수전', '변전', '전기실'],
 45: ['주차', '차로', '주차구획'],
 46: ['부설주차장', '주차대수'],
 47: ['주차구획', '주차'],
 48: ['전기차', '충전'],
 49: ['건폐율'],
 50: ['용적률'],
 51: ['지구단위'],
 52: ['개발행위'],
 53: ['개발행위'],
 54: ['도시', '군계획시설'],
 55: ['용도지역'],
 56: ['용도지구'],
 57: ['건폐율'],
 58: ['건폐율', '조례'],
 59: ['용적률'],
 60: ['공원'],
 61: ['택지개발'],
}

items = json.load(io.open(r'D:\DATA\앱개발\drawing-qc\outputs\checklist_items.json', encoding='utf-8'))
need = [it for it in items if '대상법규아님' not in it['selected']]

out = {}
for i, it in enumerate(need):
    kws = QUERIES.get(i, [])
    hits = se.search(kws) if kws else {}
    pages_summary = []
    for p in sorted(hits.keys()):
        ws = hits[p]
        pages_summary.append({
            'page': p, 'dwgno': se.dwgno(p), 'n': len(ws),
            'x': ws[0]['x'], 'y': ws[0]['y'],
            'samples': sorted(set(w['text'] for w in ws))[:8],
        })
    out[i] = {
        'source': it['source'], 'no': it['no'], 'law': it['law'], 'field': it['field'],
        'selected': it['selected'], 'keywords': kws, 'hits': pages_summary,
    }

json.dump(out, io.open(r'D:\DATA\앱개발\drawing-qc\outputs\evidence_search.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print('done, items:', len(out))
