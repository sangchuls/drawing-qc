# -*- coding: utf-8 -*-
import json, io

with io.open(r"D:\DATA\앱개발\drawing-qc\outputs\extracted.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def words_on_page(p):
    return [w for w in data if w["page"] == p]

def show(p, filt=None, ymin=None, ymax=None):
    out = []
    for w in words_on_page(p):
        if filt and filt not in w["text"]:
            continue
        if ymin is not None and not (ymin <= w["y"] <= ymax):
            continue
        out.append(w)
    out.sort(key=lambda w: (w["y"], w["x"]))
    return out

import sys
out = io.open(r"D:\DATA\앱개발\drawing-qc\outputs\qc_query_out.txt", "w", encoding="utf-8")

for p in [1,2,3,51,69,70]:
    out.write(f"=== page {p} NONE/scale tokens (y 0-120) ===\n")
    for w in show(p, ymin=0, ymax=120):
        out.write(f"{w['text']!r} x={w['x']:.1f} y={w['y']:.1f}\n")
    out.write("\n")

out.close()
print("done")
