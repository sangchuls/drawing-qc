# -*- coding: utf-8 -*-
"""Search extracted.json (all 85 drawing pages) for keyword evidence and
report which drawing number(s) each hit falls on. Used to re-verify checklist
items against the full drawing set instead of only the first few pages."""
import json, re, io
from collections import defaultdict

EXTRACTED = r'D:\DATA\앱개발\drawing-qc\outputs\extracted.json'
OWNNUM = r'D:\DATA\앱개발\drawing-qc\outputs\ownnum.txt'

_data = None
_pagemap = None

def load():
    global _data, _pagemap
    if _data is None:
        _data = json.load(io.open(EXTRACTED, encoding='utf-8'))
    if _pagemap is None:
        _pagemap = {}
        for line in io.open(OWNNUM, encoding='utf-8'):
            m = re.match(r'^(\d+)\s+(\S+)', line.strip())
            if m:
                _pagemap[int(m.group(1))] = m.group(2)
    return _data, _pagemap

def dwgno(page):
    _, pm = load()
    return pm.get(page, '?')

def search(keywords, pages=None):
    """keywords: list of substrings (OR match). pages: optional iterable to
    restrict search. Returns dict page -> list of matched word dicts."""
    data, pm = load()
    if isinstance(keywords, str):
        keywords = [keywords]
    hits = defaultdict(list)
    for w in data:
        if pages is not None and w['page'] not in pages:
            continue
        t = w['text']
        if any(k in t for k in keywords):
            hits[w['page']].append(w)
    return dict(hits)

def summarize(keywords, pages=None, max_pages=30):
    hits = search(keywords, pages)
    lines = []
    for p in sorted(hits.keys())[:max_pages]:
        ws = hits[p]
        sample_texts = ', '.join(sorted(set(w['text'] for w in ws)))[:160]
        cx = ws[0]['x']; cy = ws[0]['y']
        lines.append(f"p{p}({dwgno(p)}) n={len(ws)} x={cx:.0f} y={cy:.0f} :: {sample_texts}")
    return lines

if __name__ == '__main__':
    import sys
    kws = sys.argv[1:]
    for line in summarize(kws):
        print(line)
