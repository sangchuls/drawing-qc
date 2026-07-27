# -*- coding: utf-8 -*-
import json, io

with io.open(r"D:\DATA\앱개발\drawing-qc\outputs\extracted.json", "r", encoding="utf-8") as f:
    data = json.load(f)

p1 = [w for w in data if w["page"] == 1]

out = io.open(r"D:\DATA\앱개발\drawing-qc\outputs\qc_query_out3.txt", "w", encoding="utf-8")

# Find label token positions
for label in ["프로젝트번호", "도면번호", "Project", "Drawing"]:
    out.write(f"--- label containing '{label}' ---\n")
    for w in p1:
        if label in w["text"]:
            out.write(f"{w['text']!r} x={w['x']:.1f} y={w['y']:.1f}\n")
    out.write("\n")

# Dump all tokens within y=[55,70] sorted by x descending to see the row structure near A-000/A-001 area
out.write("--- row y in [55,68] sorted by x desc ---\n")
row = [w for w in p1 if 55 <= w["y"] <= 68]
row.sort(key=lambda w: -w["x"])
for w in row:
    out.write(f"{w['text']!r} x={w['x']:.1f} y={w['y']:.1f}\n")

out.write("\n--- row y in [280,290] (project no row?) sorted by x desc ---\n")
row2 = [w for w in p1 if 280 <= w["y"] <= 292]
row2.sort(key=lambda w: -w["x"])
for w in row2:
    out.write(f"{w['text']!r} x={w['x']:.1f} y={w['y']:.1f}\n")

out.close()
print("done")
