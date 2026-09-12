"""Gemini (Google) backend for the AI review — uses the google-genai SDK's
function-calling loop."""
import os

from google import genai
from google.genai import types

from . import common

MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")

TOOL = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name=common.SEARCH_TOOL_NAME,
        description=common.SEARCH_TOOL_DESCRIPTION,
        parameters=common.SEARCH_TOOL_PARAMETERS,
    ),
    types.FunctionDeclaration(
        name=common.SUBMIT_TOOL_NAME,
        description=common.SUBMIT_TOOL_DESCRIPTION,
        parameters=common.SUBMIT_TOOL_PARAMETERS,
    ),
])
CONFIG = types.GenerateContentConfig(tools=[TOOL])


def run(items: list[dict], words: list[dict], dwgno_map: dict[int, str],
        api_key: str, on_progress=None) -> list[dict]:
    client = genai.Client(api_key=api_key)
    search_fn = common.make_search_fn(words, dwgno_map)

    applicable_idx, na_idx = common.split_applicable(items)
    verdicts: dict[int, dict] = {
        i: {"result": "n/a", "comment": "체크리스트에서 대상법규아님으로 선언됨"} for i in na_idx
    }
    if not applicable_idx:
        return common.apply_verdicts(items, verdicts)

    applicable_items = [items[i] for i in applicable_idx]
    contents = [types.Content(role="user", parts=[types.Part(text=common.build_prompt(applicable_items))])]

    for _ in range(common.MAX_TOOL_ITERATIONS):
        if on_progress:
            on_progress()
        resp = client.models.generate_content(model=MODEL, contents=contents, config=CONFIG)
        candidate = resp.candidates[0]
        contents.append(candidate.content)

        function_calls = [p.function_call for p in (candidate.content.parts or []) if p.function_call]
        if not function_calls:
            break

        response_parts = []
        submitted = False
        for fc in function_calls:
            args = dict(fc.args or {})
            if fc.name == common.SEARCH_TOOL_NAME:
                result = search_fn(args.get("keywords", []))
                response_parts.append(types.Part.from_function_response(name=fc.name, response=result))
            elif fc.name == common.SUBMIT_TOOL_NAME:
                common.collect_submitted(args, applicable_idx, applicable_items, verdicts)
                response_parts.append(types.Part.from_function_response(name=fc.name, response={"status": "received"}))
                submitted = True

        contents.append(types.Content(role="user", parts=response_parts))
        if submitted:
            break

    for i in applicable_idx:
        verdicts.setdefault(i, {"result": "check", "comment": "AI 검토가 완료되지 못해 수동 확인이 필요합니다."})

    return common.apply_verdicts(items, verdicts)
