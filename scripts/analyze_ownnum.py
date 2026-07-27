import json, re, sys
from collections import defaultdict

with open('outputs/extracted.json', encoding='utf-8') as f:
    data = json.load(f)

pages = defaultdict(list)
for d in data:
    pages[d['page']].append(d)

out = []
prev_num = None
for pno in range(1, 86):
    toks = pages[pno]
    # title-block drawing number column: x between 15 and 40, y between 1110 and 1140
    col = [t for t in toks if 15 <= t['x'] <= 40 and 1110 <= t['y'] <= 1140]
    col_sorted = sorted(col, key=lambda t: t['y'])
    text = ''.join(t['text'] for t in col_sorted)
    xs = [t['x'] for t in col_sorted]
    ys = [t['y'] for t in col_sorted]
    out.append(f"{pno}\t{text}\t(n={len(col_sorted)}, x={xs}, y={ys})")

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
