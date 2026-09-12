"""Grok (xAI) backend for the AI review. xAI's API is OpenAI-Chat-Completions
compatible, so this reuses the same loop with a different base_url/model."""
import os

from . import _openai_compatible

MODEL = os.environ.get("XAI_MODEL", "grok-2-latest")
BASE_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1")


def run(items: list[dict], words: list[dict], dwgno_map: dict[int, str],
        api_key: str, on_progress=None) -> list[dict]:
    return _openai_compatible.run(items, words, dwgno_map, api_key, model=MODEL, base_url=BASE_URL, on_progress=on_progress)
