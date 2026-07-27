import sys, json, fitz   # pymupdf

def extract(pdf_path):
    doc = fitz.open(pdf_path)
    items = []
    for pno, page in enumerate(doc, start=1):
        for w in page.get_text('words'):
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            items.append({'page': pno, 'text': text,
                          'x': round((x0+x1)/2, 1),
                          'y': round((y0+y1)/2, 1)})
    return items

if __name__ == '__main__':
    data = extract(sys.argv[1])
    print(json.dumps(data, ensure_ascii=False))
