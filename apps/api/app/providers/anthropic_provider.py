"""Claude (Anthropic) backend for the AI review — uses the native tool-use loop."""
import json
import os

import anthropic

from . import common

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

SEARCH_TOOL = {
    "name": common.SEARCH_TOOL_NAME,
    "description": common.SEARCH_TOOL_DESCRIPTION,
    "input_schema": common.SEARCH_TOOL_PARAMETERS,
}
SUBMIT_TOOL = {
    "name": common.SUBMIT_TOOL_NAME,
    "description": common.SUBMIT_TOOL_DESCRIPTION,
    "input_schema": common.SUBMIT_TOOL_PARAMETERS,
}


def run(items: list[dict], words: list[dict], dwgno_map: dict[int, str],
        api_key: str, on_progress=None) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)
    search_fn = common.make_search_fn(words, dwgno_map)

    applicable_idx, na_idx = common.split_applicable(items)
    verdicts: dict[int, dict] = {
        i: {"result": "n/a", "comment": "체크리스트에서 대상법규아님으로 선언됨"} for i in na_idx
    }
    if not applicable_idx:
        return common.apply_verdicts(items, verdicts)

    applicable_items = [items[i] for i in applicable_idx]
    messages = [{"role": "user", "content": common.build_prompt(applicable_items)}]

    for _ in range(common.MAX_TOOL_ITERATIONS):
        if on_progress:
            on_progress()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=[SEARCH_TOOL, SUBMIT_TOOL],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break

        tool_results = []
        submitted = False
        for tu in tool_uses:
            if tu.name == common.SEARCH_TOOL_NAME:
                result = search_fn(tu.input.get("keywords", []))
                tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": json.dumps(result, ensure_ascii=False)})
            elif tu.name == common.SUBMIT_TOOL_NAME:
                common.collect_submitted(tu.input, applicable_idx, applicable_items, verdicts)
                tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": "received"})
                submitted = True

        messages.append({"role": "user", "content": tool_results})
        if submitted:
            break

    for i in applicable_idx:
        verdicts.setdefault(i, {"result": "check", "comment": "AI 검토가 완료되지 못해 수동 확인이 필요합니다."})

    return common.apply_verdicts(items, verdicts)
