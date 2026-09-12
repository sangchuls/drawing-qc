"""Provider-agnostic pieces shared by every LLM backend: the prompt, the
schema for the two tools (search / submit), the local search implementation,
and turning raw verdicts back into the item list. Only the tool-calling loop
itself (message format, SDK calls) differs per provider.
"""
from collections import defaultdict

MAX_TOOL_ITERATIONS = 40

SEARCH_TOOL_NAME = "search_drawing_text"
SUBMIT_TOOL_NAME = "submit_results"

SEARCH_TOOL_DESCRIPTION = (
    "Search the extracted drawing text (all pages) for any of the given "
    "keywords (substring match, OR). Returns, per matching page, the "
    "drawing number, a representative x/y coordinate, and sample matched "
    "text — so you can judge whether it's real evidence for a checklist item."
)
SEARCH_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Korean/English keyword substrings to search for, OR-matched.",
        }
    },
    "required": ["keywords"],
}

SUBMIT_TOOL_DESCRIPTION = "Submit the final review verdict for every checklist item given in the prompt."
SUBMIT_TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_index": {"type": "integer", "description": "0-based index into the item list you were given"},
                    "result": {"type": "string", "enum": ["pass", "check", "error", "n/a"]},
                    "page": {"type": "integer", "description": "0 if no location applies"},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "dwgno_list": {"type": "array", "items": {"type": "string"}},
                    "comment": {"type": "string", "description": "Korean, 1-2 sentences, cite what was found or why not found"},
                },
                "required": ["item_index", "result", "comment"],
            },
        }
    },
    "required": ["results"],
}


def make_search_fn(words: list[dict], dwgno_map: dict[int, str]):
    def search(keywords: list[str]) -> dict:
        hits = defaultdict(list)
        for w in words:
            if any(k in w["text"] for k in keywords):
                hits[w["page"]].append(w)
        pages = []
        for p in sorted(hits.keys())[:25]:
            ws = hits[p]
            pages.append({
                "page": p,
                "dwgno": dwgno_map.get(p, "?"),
                "n": len(ws),
                "x": ws[0]["x"], "y": ws[0]["y"],
                "samples": sorted(set(w["text"] for w in ws))[:6],
            })
        return {"pages": pages}
    return search


def build_prompt(items: list[dict]) -> str:
    lines = [
        "당신은 건축 도면 QC/법규 검토 전문가입니다. 아래 체크리스트 항목을 도면 텍스트와 대조해 검토하세요.",
        "",
        "규칙:",
        "- 각 항목에 대해 search_drawing_text 툴로 관련 키워드를 검색해 실제 도면에 근거가 있는지 확인하세요.",
        "- '대상법규아님'처럼 이미 비적용으로 선언된 항목은 검색 없이 result=n/a로 처리하세요.",
        "- 선언값이 '비대상/해당없음' 계열인데 검색 결과가 없으면, 그 부재 자체가 선언과 부합하므로 result=pass로 처리하세요.",
        "- 선언값이 '대상/적합' 계열인데 검색으로 실제 근거(도면번호)를 찾으면 result=pass, 못 찾으면 result=check으로 처리하세요.",
        "- 도면과 명백히 모순되는 근거를 찾은 경우에만 result=error를 사용하세요.",
        "- 근거를 찾지 못한 항목은 page/x/y를 생략하거나 0으로 두세요 (가짜 좌표를 만들지 마세요).",
        "- 모든 항목을 다 검토한 뒤 submit_results 툴을 한 번만 호출해 전체 결과를 제출하세요.",
        "",
        "체크리스트 항목:",
    ]
    for i, it in enumerate(items):
        decl = f" (선언값: {', '.join(it['selected'])})" if it.get("selected") else ""
        lines.append(f"[{i}] {it['law']} - {it['field']}{decl}")
    return "\n".join(lines)


def split_applicable(items: list[dict]) -> tuple[list[int], list[int]]:
    applicable_idx = [i for i, it in enumerate(items) if it.get("applicable", True)]
    na_idx = [i for i, it in enumerate(items) if not it.get("applicable", True)]
    return applicable_idx, na_idx


def collect_submitted(tool_input: dict, applicable_idx: list[int], applicable_items: list[dict],
                       verdicts: dict[int, dict]) -> None:
    for r in tool_input.get("results", []):
        local_idx = r.get("item_index")
        if local_idx is None or not (0 <= local_idx < len(applicable_items)):
            continue
        verdicts[applicable_idx[local_idx]] = r


def apply_verdicts(items: list[dict], verdicts: dict[int, dict]) -> list[dict]:
    out = []
    for i, it in enumerate(items):
        v = verdicts.get(i, {"result": "check", "comment": "검토되지 않음"})
        out.append({
            **it,
            "result": v.get("result", "check"),
            "page": v.get("page") or 0,
            "x": v.get("x") or 0,
            "y": v.get("y") or 0,
            "dwgno_list": v.get("dwgno_list") or [],
            "comment": v.get("comment", ""),
            "located": bool(v.get("page")),
        })
    return out
