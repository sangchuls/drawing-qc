"""Shared tool-calling loop for any OpenAI-Chat-Completions-compatible API.
Used by both the OpenAI (GPT) and xAI (Grok) providers, which only differ in
`base_url` and default model.
"""
import json

from openai import OpenAI

from . import common

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": common.SEARCH_TOOL_NAME,
            "description": common.SEARCH_TOOL_DESCRIPTION,
            "parameters": common.SEARCH_TOOL_PARAMETERS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": common.SUBMIT_TOOL_NAME,
            "description": common.SUBMIT_TOOL_DESCRIPTION,
            "parameters": common.SUBMIT_TOOL_PARAMETERS,
        },
    },
]


def run(items: list[dict], words: list[dict], dwgno_map: dict[int, str], api_key: str,
        model: str, base_url: str | None = None, on_progress=None) -> list[dict]:
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
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
        resp = client.chat.completions.create(
            model=model,
            tools=TOOLS,
            messages=messages,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        tool_calls = msg.tool_calls or []
        if not tool_calls:
            break

        submitted = False
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if tc.function.name == common.SEARCH_TOOL_NAME:
                result = search_fn(args.get("keywords", []))
                content = json.dumps(result, ensure_ascii=False)
            elif tc.function.name == common.SUBMIT_TOOL_NAME:
                common.collect_submitted(args, applicable_idx, applicable_items, verdicts)
                content = "received"
                submitted = True
            else:
                content = "unknown tool"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})

        if submitted:
            break

    for i in applicable_idx:
        verdicts.setdefault(i, {"result": "check", "comment": "AI 검토가 완료되지 못해 수동 확인이 필요합니다."})

    return common.apply_verdicts(items, verdicts)
