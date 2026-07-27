"""Parses uploaded checklist files into a flat list of checklist items.

Supports three shapes:
  1. The standard Korean "한국건축규정체크리스트" PDF form (건축법 별표2) —
     numbered items with □/■ checkbox choices. This is the format ported
     from the original Claude Code session's scripts/parse_checklist.py.
  2. A plain Excel checklist (.xlsx/.xls) — each row becomes one item.
  3. No checklist uploaded — falls back to the default item list from the
     original drawing-review SKILL.md.
"""
import io
import re

import fitz
import openpyxl

NEG_PREFIXES = ("비대상", "해당없음", "검토제외")

DEFAULT_ITEMS = [
    {"source": "기본(법규)", "law": "피난거리", "field": "", "selected": [], "applicable": True},
    {"source": "기본(법규)", "law": "복도/계단 폭", "field": "", "selected": [], "applicable": True},
    {"source": "기본(법규)", "law": "방화구획", "field": "", "selected": [], "applicable": True},
    {"source": "기본(법규)", "law": "비상구", "field": "", "selected": [], "applicable": True},
    {"source": "기본(법규)", "law": "주차대수", "field": "", "selected": [], "applicable": True},
    {"source": "기본(QC)", "law": "도면 누락", "field": "", "selected": [], "applicable": True},
    {"source": "기본(QC)", "law": "치수 불일치", "field": "", "selected": [], "applicable": True},
    {"source": "기본(QC)", "law": "범례/축척 표기", "field": "", "selected": [], "applicable": True},
    {"source": "기본(QC)", "law": "도면번호 연속성", "field": "", "selected": [], "applicable": True},
]


# ---- standard 법규 체크리스트 PDF form ----

def _extract_plain_text_lines(pdf_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    lines: list[str] = []
    for page in doc:
        for raw in page.get_text().splitlines():
            raw = raw.strip()
            if raw:
                lines.append(raw)
    return lines


def _looks_like_standard_form(lines: list[str]) -> bool:
    mark_count = sum(l.count("■") + l.count("□") for l in lines)
    return mark_count >= 10


def _split_embedded_marks(line: str) -> list[str]:
    out = []
    rest = line
    while True:
        idx = None
        for i, ch in enumerate(rest):
            if i == 0:
                continue
            if ch in ("□", "■"):
                idx = i
                break
        if idx is None:
            out.append(rest)
            break
        out.append(rest[:idx])
        rest = rest[idx:]
    return out


def _is_choice(line: str) -> bool:
    return line.startswith("□") or line.startswith("■")


def _parse_standard_form(lines: list[str], source_label: str) -> list[dict]:
    flat: list[str] = []
    for l in lines:
        flat.extend(_split_embedded_marks(l))
    flat = [l for l in flat if l.strip()]

    num_idx = [i for i, l in enumerate(flat) if re.fullmatch(r"\d{1,3}", l)]
    blocks: dict[int, list[list[str]]] = {}
    for k, idx in enumerate(num_idx):
        end = num_idx[k + 1] if k + 1 < len(num_idx) else len(flat)
        num = int(flat[idx])
        blocks.setdefault(num, []).append(flat[idx + 1:end])

    def split_title(block_lines: list[str]):
        title_lines = []
        i = 0
        for i, line in enumerate(block_lines):
            if _is_choice(line):
                break
            title_lines.append(line)
            if ")" in line:
                i += 1
                break
        else:
            i = len(block_lines)
        return title_lines, block_lines[i:]

    items = []
    for num in sorted(blocks.keys()):
        candidates = blocks[num]
        first_title, rest_all = split_title(candidates[0])
        for extra in candidates[1:]:
            _, extra_rest = split_title(extra)
            rest_all = rest_all + extra_rest

        state = "label"
        cur_label: list[str] = []
        cur_choices: list[str] = []
        subfields: list[tuple[list[str], list[str]]] = []
        for line in rest_all:
            if _is_choice(line):
                state = "choices"
                cur_choices.append(line)
            else:
                if state == "choices":
                    subfields.append((cur_label, cur_choices))
                    cur_label = [line]
                    cur_choices = []
                    state = "label"
                else:
                    cur_label.append(line)
        if cur_label or cur_choices:
            subfields.append((cur_label, cur_choices))

        law_title = "".join(first_title)

        merged: dict[str, list[str]] = {}
        order: list[str] = []
        for label_lines, choice_lines in subfields:
            label = "".join(label_lines).strip()
            if not label and not choice_lines:
                continue
            merged.setdefault(label, [])
            if label not in order:
                order.append(label)
            merged[label].extend(choice_lines)

        for label in order:
            choice_lines = merged[label]
            selected = [c[1:].strip() for c in choice_lines if c.startswith("■")]
            if not label:
                continue
            na = any(s.startswith("대상법규아님") for s in selected)
            items.append({
                "source": source_label,
                "law": law_title,
                "field": label.replace("\xa0", " "),
                "selected": selected,
                "applicable": not na,
            })
    return items


# ---- Excel checklist ----

def _parse_excel(xlsx_bytes: bytes, source_label: str) -> list[dict]:
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    items = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        for row in rows[1:]:  # skip header row
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if not cells:
                continue
            items.append({
                "source": source_label,
                "law": cells[0],
                "field": " / ".join(cells[1:]) if len(cells) > 1 else "",
                "selected": [],
                "applicable": True,
            })
    return items


# ---- entry point ----

def parse_checklist_files(files: list[tuple[str, bytes]]) -> list[dict]:
    """files: list of (filename, content_bytes). Returns [] if none given
    (caller should fall back to DEFAULT_ITEMS)."""
    all_items: list[dict] = []
    for filename, content in files:
        lower = filename.lower()
        if lower.endswith((".xlsx", ".xls")):
            all_items.extend(_parse_excel(content, filename))
        elif lower.endswith(".pdf"):
            lines = _extract_plain_text_lines(content)
            if _looks_like_standard_form(lines):
                all_items.extend(_parse_standard_form(lines, filename))
            else:
                # unrecognized PDF layout: fall back to one item per non-empty line
                for line in lines:
                    if len(line) > 3:
                        all_items.append({
                            "source": filename, "law": line, "field": "",
                            "selected": [], "applicable": True,
                        })
    return all_items
