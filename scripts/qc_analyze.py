# -*- coding: utf-8 -*-
import re, ast, io

lines = io.open(r"D:\DATA\앱개발\drawing-qc\outputs\dwgnum.txt", encoding="utf-8").read().splitlines()

# parse line 1 (page 1) for full and paired lists
line1 = lines[0]
full_m = re.search(r"full:(\[.*?\])\s*paired:(\[.*\])", line1)
full_list = ast.literal_eval(full_m.group(1))
paired_list = ast.literal_eval(full_m.group(2))
paired_nums = [t[0] for t in paired_list]

index_set = set(full_list) | set(paired_nums)

def sortkey(s):
    m = re.match(r"A-(\d+)([a-z]?)", s)
    if m:
        return (int(m.group(1)), m.group(2))
    return (99999, s)

index_sorted = sorted(index_set, key=sortkey)
print("INDEX total unique:", len(index_sorted))
print(index_sorted)

# own 84 sheets from pages 2-85 paired column (own drawing number per page)
own = {}
for ln in lines[1:]:
    m = re.match(r"^(\d+)\s+\d+\s+full:\[.*?\]\s*paired:\[(.*)\]\s*$", ln)
    pno = int(re.match(r"^(\d+)", ln).group(1))
    pm = re.search(r"paired:\[(.*)\]$", ln)
    inner = pm.group(1)
    if inner.strip() == "":
        own[pno] = None
    else:
        tup = ast.literal_eval("[" + inner + "]")
        own[pno] = tup[0][0]

# manual fix from direct fitz confirmation: page 2 = A-001a
own[2] = "A-001a"

own_seq = [own[p] for p in range(2,86)]
print("\nOWN sequence len:", len(own_seq))
print(own_seq)

# duplicates check
from collections import Counter
c = Counter(own_seq)
dups = {k:v for k,v in c.items() if v>1}
print("\nDUPLICATES:", dups)

# order check (monotonic by sortkey)
keys = [sortkey(x) for x in own_seq]
inversions = []
for i in range(1,len(keys)):
    if keys[i] < keys[i-1]:
        inversions.append((i+1, own_seq[i-1], own_seq[i]))  # page index approx
print("INVERSIONS (page_pos, prev, curr):", inversions)

own_set = set(own_seq)
missing_from_pdf = [x for x in index_sorted if x not in own_set]
print("\nMISSING (in index, not in actual 84 sheets), count:", len(missing_from_pdf))
print(missing_from_pdf)

extra_in_pdf_not_index = [x for x in own_seq if x not in index_set]
print("\nIN PDF but NOT in page1 index:", extra_in_pdf_not_index)
