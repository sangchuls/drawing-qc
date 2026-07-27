# -*- coding: utf-8 -*-
import fitz
import io

doc = fitz.open(r"D:\DATA\앱개발\drawing-qc\inputs\도면\건축도면.pdf")

out = io.open(r"D:\DATA\앱개발\drawing-qc\outputs\qc_explore_dump2.txt", "w", encoding="utf-8")

def dump_page(pno):
    page = doc[pno-1]
    out.write(f"===== PAGE {pno} rotation={page.rotation} mediabox={page.mediabox} =====\n")
    text = page.get_text()
    out.write(text[:4000])
    out.write("\n----- END -----\n\n")

for pno in [2,3,51,69,70]:
    dump_page(pno)

out.close()
print("done")
