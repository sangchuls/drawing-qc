# -*- coding: utf-8 -*-
"""Parse the raw extracted checklist text (law_*.pdf.txt) into structured items."""
import json, re, sys, io

def load_lines(path):
    lines = []
    for raw in io.open(path, encoding='utf-8'):
        raw = raw.rstrip('\n')
        if raw.strip().startswith('--- page'):
            continue
        if raw.strip() == '':
            continue
        lines.append(raw.strip())
    return lines

def split_embedded_marks(line):
    """A rendering glitch sometimes merges 'label■choice' onto one line. Split it."""
    out = []
    rest = line
    while True:
        idx = None
        for i, ch in enumerate(rest):
            if i == 0:
                continue
            if ch in ('□', '■'):
                idx = i
                break
        if idx is None:
            out.append(rest)
            break
        out.append(rest[:idx])
        rest = rest[idx:]
    return out

def is_choice(line):
    return line.startswith('□') or line.startswith('■')

def parse_file(path, source_label):
    raw_lines = load_lines(path)
    lines = []
    for l in raw_lines:
        lines.extend(split_embedded_marks(l))
    lines = [l for l in lines if l.strip() != '']

    # locate item-number line indices (pure digits, length<=3), skip the
    # first occurrence-context lines like "1 . 건축허가시..." handled since that's not pure digit
    num_idx = [i for i, l in enumerate(lines) if re.fullmatch(r'\d{1,3}', l)]

    blocks = {}
    for k, idx in enumerate(num_idx):
        end = num_idx[k + 1] if k + 1 < len(num_idx) else len(lines)
        num = int(lines[idx])
        block_lines = lines[idx + 1:end]
        blocks.setdefault(num, []).append(block_lines)

    def split_title(block_lines):
        """Return (title_lines, remainder_lines): title = leading non-choice
        lines up to and including the line that closes the '...조(...)' paren."""
        title_lines = []
        i = 0
        for i, line in enumerate(block_lines):
            if is_choice(line):
                break
            title_lines.append(line)
            if ')' in line:
                i += 1
                break
        else:
            i = len(block_lines)
        return title_lines, block_lines[i:]

    items = []
    for num in sorted(blocks.keys()):
        candidates = blocks[num]
        # page-break rendering repeats the item number + law title on the
        # next page; strip the repeated title from every candidate after the
        # first, then concatenate the remainders so split rows merge correctly
        first_title, rest_all = split_title(candidates[0])
        for extra in candidates[1:]:
            _, extra_rest = split_title(extra)
            rest_all = rest_all + extra_rest

        state = 'label'
        cur_label = []
        cur_choices = []
        subfields = []
        for line in rest_all:
            if is_choice(line):
                state = 'choices'
                cur_choices.append(line)
            else:
                if state == 'choices':
                    subfields.append((cur_label, cur_choices))
                    cur_label = [line]
                    cur_choices = []
                    state = 'label'
                else:
                    cur_label.append(line)
        if cur_label or cur_choices:
            subfields.append((cur_label, cur_choices))

        law_title = ''.join(first_title)

        # merge subfields sharing the same label (split across a page break)
        merged = {}
        order = []
        for label_lines, choice_lines in subfields:
            label = ''.join(label_lines).strip()
            if not label and not choice_lines:
                continue
            if label not in merged:
                merged[label] = []
                order.append(label)
            merged[label].extend(choice_lines)

        for label in order:
            choice_lines = merged[label]
            selected = [c[1:].strip() for c in choice_lines if c.startswith('■')]
            all_choices = [c[1:].strip() for c in choice_lines]
            items.append({
                'source': source_label,
                'no': num,
                'law': law_title,
                'field': label,
                'selected': selected,
                'choices': all_choices,
            })
    return items

if __name__ == '__main__':
    items1 = parse_file(r'D:\DATA\앱개발\drawing-qc\outputs\law_건축물관련법규.pdf.txt', '건축물관련법규')
    items2 = parse_file(r'D:\DATA\앱개발\drawing-qc\outputs\law_입지관련법규.pdf.txt', '입지관련법규')
    all_items = items1 + items2

    total_marks = sum(len(it['selected']) for it in all_items)
    no_select = [it for it in all_items if not it['selected']]

    log = []
    log.append(f'items1(건축물관련): {len(items1)}  items2(입지관련): {len(items2)}  total rows: {len(all_items)}')
    log.append(f'total selected(■) marks: {total_marks}')
    log.append(f'rows with NO ■ selection (needs manual check): {len(no_select)}')
    for it in no_select:
        log.append(f"  {it['source']} {it['no']} {it['law'][:30]} | {it['field']} | choices={it['choices']}")

    with io.open(r'D:\DATA\앱개발\drawing-qc\outputs\_parse_report.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(log))

    with io.open(r'D:\DATA\앱개발\drawing-qc\outputs\checklist_items.json', 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print('done, see outputs/_parse_report.txt')
