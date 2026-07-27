"""Extracts text+coordinates from every page of the uploaded drawing PDF,
and auto-detects each page's title-block drawing number (e.g. "A-101").

The drawing-number detection generalizes what was done by hand for the
하남미사 test drawing in the original Claude Code session: title blocks
place the drawing-number field at (almost) the same (x, y) on every sheet,
so the most common location of a drawing-number-shaped token across all
pages is very likely that field.
"""
import re
import fitz  # pymupdf

DWGNO_RE = re.compile(r"^[A-Z]{1,4}-\d{2,5}[A-Za-z]?$")
PREFIX_RE = re.compile(r"^[A-Z]{1,4}-$")
SUFFIX_RE = re.compile(r"^\d{2,5}[A-Za-z]?$")
BUCKET = 6  # pt, coordinate rounding for clustering title-block position
PAIR_MAX_DIST = 20  # pt, max distance to pair a split "A-" + "001" token


def extract_words(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    words = []
    for pno, page in enumerate(doc, start=1):
        for w in page.get_text("words"):
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            words.append({
                "page": pno, "text": text,
                "x": round((x0 + x1) / 2, 1),
                "y": round((y0 + y1) / 2, 1),
            })
    return words


def page_count(pdf_path: str) -> int:
    return fitz.open(pdf_path).page_count


def _paired_candidates(words: list[dict]) -> list[dict]:
    """Some title blocks render the drawing number as two separate word
    tokens (e.g. rotated/vertical text splits "A-001" into "A-" and "001").
    Pair up nearby prefix/suffix tokens on the same page and synthesize a
    combined candidate, in addition to any tokens that already match whole."""
    by_page: dict[int, list[dict]] = {}
    for w in words:
        by_page.setdefault(w["page"], []).append(w)

    combined = []
    for page_words in by_page.values():
        prefixes = [w for w in page_words if PREFIX_RE.match(w["text"])]
        suffixes = [w for w in page_words if SUFFIX_RE.match(w["text"])]
        for p in prefixes:
            best, best_dist = None, PAIR_MAX_DIST
            for s in suffixes:
                if abs(s["x"] - p["x"]) > 3:
                    continue
                dist = abs(s["y"] - p["y"])
                if dist < best_dist:
                    best, best_dist = s, dist
            if best:
                combined.append({
                    "page": p["page"], "text": p["text"] + best["text"],
                    "x": p["x"], "y": (p["y"] + best["y"]) / 2,
                })
    return combined


def detect_drawing_numbers(words: list[dict], n_pages: int) -> dict[int, str]:
    """Returns {page_number: drawing_no}. Falls back to '?' for pages where
    no confident match is found."""
    candidates = [w for w in words if DWGNO_RE.match(w["text"])]
    candidates += [c for c in _paired_candidates(words) if DWGNO_RE.match(c["text"])]
    if not candidates:
        return {}

    # cluster by rounded (x, y) bucket, count how many distinct pages each
    # bucket appears on — the title-block field will appear on nearly every page
    bucket_pages: dict[tuple[int, int], set[int]] = {}
    for w in candidates:
        b = (round(w["x"] / BUCKET), round(w["y"] / BUCKET))
        bucket_pages.setdefault(b, set()).add(w["page"])

    best_bucket = max(bucket_pages, key=lambda b: len(bucket_pages[b]))
    coverage = len(bucket_pages[best_bucket]) / n_pages
    if coverage < 0.5:
        return {}  # no consistent title-block position found; not confident enough

    bx, by = best_bucket
    target_x, target_y = bx * BUCKET, by * BUCKET

    result: dict[int, str] = {}
    for w in candidates:
        if abs(w["x"] - target_x) <= BUCKET * 1.5 and abs(w["y"] - target_y) <= BUCKET * 1.5:
            # prefer the first match per page (title blocks contain one drawing-no field)
            result.setdefault(w["page"], w["text"])
    return result
