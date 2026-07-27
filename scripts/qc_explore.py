import fitz
import re
import json

doc = fitz.open(r"D:\DATA\앱개발\drawing-qc\inputs\도면\건축도면.pdf")

def dump_page(pno, tag):
    page = doc[pno-1]
    print(f"===== PAGE {pno} ({tag}) rotation={page.rotation} =====")
    text = page.get_text()
    print(text[:3000])
    print("----- END -----\n")

for pno in [1,2,3,51,69,70]:
    dump_page(pno, "")
