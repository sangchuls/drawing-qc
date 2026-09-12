"""GPT (OpenAI) backend for the AI review."""
import os

from . import _openai_compatible

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")


def run(items: list[dict], words: list[dict], dwgno_map: dict[int, str],
        api_key: str, on_progress=None) -> list[dict]:
    return _openai_compatible.run(items, words, dwgno_map, api_key, model=MODEL, on_progress=on_progress)
