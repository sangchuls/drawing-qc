"""Draws revision-cloud markers + comment boxes on the drawing PDF for every
checklist item that has a real (located) drawing anchor. Ported from the
original Claude Code session's scripts/mark.py, including the collision-
avoidance fix (clouds/boxes no longer stack on top of each other) and the
"skip items with no genuine location" behavior — both added after the user
reported overlapping markup in that session.
"""
import math
import os

import fitz

BLUE = (0, 0.3, 0.9)
RED = (0.85, 0, 0)

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
FONT = os.path.join(_FONT_DIR, "NanumGothic-Regular.ttf")
FONT_BOLD = os.path.join(_FONT_DIR, "NanumGothic-Bold.ttf")


def draw_cloud(page, rect, color, bump=5, chord=14, width=1.2):
    cx = (rect.x0 + rect.x1) / 2
    cy = (rect.y0 + rect.y1) / 2
    corners = [rect.tl, rect.tr, rect.br, rect.bl, rect.tl]
    shape = page.new_shape()
    for i in range(4):
        p0, p1 = corners[i], corners[i + 1]
        dx, dy = p1.x - p0.x, p1.y - p0.y
        length = math.hypot(dx, dy)
        n = max(3, round(length / chord))
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        midx, midy = (p0.x + p1.x) / 2, (p0.y + p1.y) / 2
        if (midx - cx) * nx + (midy - cy) * ny < 0:
            nx, ny = -nx, -ny
        k = bump * 1.33
        for j in range(n):
            a0 = fitz.Point(p0.x + dx * j / n, p0.y + dy * j / n)
            a1 = fitz.Point(p0.x + dx * (j + 1) / n, p0.y + dy * (j + 1) / n)
            c1 = fitz.Point(a0.x + nx * k, a0.y + ny * k)
            c2 = fitz.Point(a1.x + nx * k, a1.y + ny * k)
            shape.draw_bezier(a0, c1, c2, a1)
    shape.finish(color=color, width=width, closePath=False)
    shape.commit()


def overlaps(a, b, pad=3):
    return not (a.x1 + pad < b.x0 or b.x1 + pad < a.x0 or
                a.y1 + pad < b.y0 or b.y1 + pad < a.y0)


def find_free_dy(dx, dy0, box_w, box_h, placed, page_rect, step):
    dy = dy0
    tries = 0
    max_tries = int(page_rect.height // step) + 2
    while tries < max_tries:
        cand = fitz.Rect(dx, dy, dx + box_w, dy + box_h)
        if cand.y1 > page_rect.height:
            dy = 2
            tries += 1
            continue
        if not any(overlaps(cand, p) for p in placed):
            return dy
        dy += step
        tries += 1
    return dy0


def mark(pdf_in: str, results: list[dict], pdf_out: str):
    """results: list of dicts with page (1-based), x, y, color, comment,
    label(optional), located(optional, default True), w/h(optional)."""
    doc = fitz.open(pdf_in)
    placed_by_page: dict[int, list] = {}

    for r in results:
        if r.get("located") is False:
            continue

        page_idx = r["page"] - 1
        page = doc[page_idx]
        M = page.rotation_matrix
        Minv = ~M
        disp_page_rect = page.rect
        placed = placed_by_page.setdefault(page_idx, [])

        color = RED if r.get("color") == "red" else BLUE

        dhw = r.get("w", 45)
        dhh = r.get("h", 12)

        anchor_disp = fitz.Point(r["x"], r["y"]) * M

        step_y = 2 * dhh + 8
        tries = 0
        while tries < 40:
            disp_cloud = fitz.Rect(anchor_disp.x - dhw, anchor_disp.y - dhh,
                                    anchor_disp.x + dhw, anchor_disp.y + dhh)
            if not any(overlaps(disp_cloud, p) for p in placed):
                break
            anchor_disp = fitz.Point(anchor_disp.x, anchor_disp.y + step_y)
            if anchor_disp.y + dhh > disp_page_rect.height:
                anchor_disp = fitz.Point(anchor_disp.x, dhh + 4)
            tries += 1

        disp_cloud = fitz.Rect(anchor_disp.x - dhw, anchor_disp.y - dhh,
                                anchor_disp.x + dhw, anchor_disp.y + dhh)
        raw_cloud = disp_cloud * Minv
        draw_cloud(page, raw_cloud, color)
        placed.append(disp_cloud)

        label = r.get("label", "")
        comment = r.get("comment", "")
        text = (f"[{label}] {comment}" if label else comment).strip()
        if not text:
            continue

        box_w = 190
        box_h = max(16, 11 * (1 + len(text) // 24))

        dx_right = anchor_disp.x + dhw + 6
        dx_left = anchor_disp.x - dhw - box_w - 6
        if dx_right + box_w <= disp_page_rect.width:
            dx = dx_right
        elif dx_left >= 0:
            dx = dx_left
        else:
            dx = min(max(2, anchor_disp.x - box_w / 2), disp_page_rect.width - box_w - 2)

        dy0 = anchor_disp.y - dhh
        if dy0 < 0:
            dy0 = 2
        if dy0 + box_h > disp_page_rect.height:
            dy0 = disp_page_rect.height - box_h - 2

        dy = find_free_dy(dx, dy0, box_w, box_h, placed, disp_page_rect, box_h + 4)

        disp_tbox = fitz.Rect(dx, dy, dx + box_w, dy + box_h)
        raw_tbox = disp_tbox * Minv

        page.draw_rect(raw_tbox, color=color, fill=(1, 1, 1), fill_opacity=0.85, width=0.6)
        page.insert_textbox(raw_tbox, text, fontsize=7, color=color,
                             fontname="dqcfont", fontfile=FONT, align=0, rotate=page.rotation)
        placed.append(disp_tbox)

    doc.save(pdf_out)
