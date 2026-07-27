# -*- coding: utf-8 -*-
import json, io

with io.open(r"D:\DATA\앱개발\drawing-qc\outputs\extracted.json", "r", encoding="utf-8") as f:
    data = json.load(f)

out = io.open(r"D:\DATA\앱개발\drawing-qc\outputs\qc_query_out2.txt", "w", encoding="utf-8")

for p in [1,2,3,51,69,70]:
    out.write(f"=== page {p} tokens containing NONE ===\n")
    for w in data:
        if w["page"] != p:
            continue
        if "NONE" in w["text"]:
            out.write(f"{w['text']!r} x={w['x']:.1f} y={w['y']:.1f}\n")
    out.write("\n")

# also grab A1: A3: tokens and drawing number tokens context for these pages
for p in [1,2,3,51,69,70]:
    out.write(f"=== page {p} A1:/A3:/Scale/축척 tokens ===\n")
    for w in data:
        if w["page"] != p:
            continue
        t = w["text"]
        if t in ("A1:", "A3:", "Scale", "축척") or t.startswith("A1") or t.startswith("A3"):
            out.write(f"{t!r} x={w['x']:.1f} y={w['y']:.1f}\n")
    out.write("\n")

out.close()
print("done")
