import json, re, sys
from collections import defaultdict

with open('outputs/extracted.json', encoding='utf-8') as f:
    data = json.load(f)

pages = defaultdict(list)
for d in data:
    pages[d['page']].append(d)

full_pat = re.compile(r'^[A-Z]{1,2}-\d{2,4}$')

results = {}
for pno in range(1,86):
    toks = pages[pno]
    fulls = [t for t in toks if full_pat.match(t['text'])]
    prefixes = [t for t in toks if re.match(r'^[A-Z]{1,2}-$', t['text'])]
    paired = []
    for p in prefixes:
        candidates = [t for t in toks if re.match(r'^\d{2,4}$', t['text']) and abs(t['x']-p['x'])<5 and 0< (t['y']-p['y']) < 20]
        if candidates:
            best = min(candidates, key=lambda t: t['y']-p['y'])
            paired.append((p, best))
    results[pno] = (fulls, paired)

out = []
for pno in range(1,86):
    fulls, paired = results[pno]
    fs = [t['text'] for t in fulls]
    ps = [(p['text']+b['text'], p['x'], p['y']) for p,b in paired]
    out.append(f"{pno} full:{fs} paired:{ps}")

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
