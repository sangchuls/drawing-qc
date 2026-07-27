import json, sys
from collections import defaultdict

with open('outputs/extracted.json', encoding='utf-8') as f:
    data = json.load(f)

pages = defaultdict(list)
for d in data:
    pages[d['page']].append(d)

out = []
for pno in range(1, 86):
    toks = pages[pno]
    a1_val = None
    a3_val = None
    for t in toks:
        if abs(t['x'] - 67.8) < 15:
            if 1100 < t['y'] < 1115:
                a1_val = t['text']
            if 1140 < t['y'] < 1155:
                a3_val = t['text']
    out.append(f"{pno}\tA1={a1_val}\tA3={a3_val}")

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
