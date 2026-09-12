"""Multi-provider dispatch for the checklist-vs-drawing AI review.

Each provider module exposes `run(items, words, dwgno_map, api_key, on_progress=None)`
with the same contract as the original Anthropic-only `ai_review.run_ai_review`.
The user supplies their own API key per provider (pasted into the frontend and
kept in their browser) — nothing is stored server-side.
"""
from . import anthropic_provider, gemini_provider, openai_provider, xai_provider

PROVIDERS = {
    "anthropic": anthropic_provider.run,
    "openai": openai_provider.run,
    "google": gemini_provider.run,
    "xai": xai_provider.run,
}


def run_review(provider: str, items: list[dict], words: list[dict],
                dwgno_map: dict[int, str], api_key: str, on_progress=None) -> list[dict]:
    fn = PROVIDERS.get(provider)
    if fn is None:
        raise ValueError(f"지원하지 않는 LLM 제공자입니다: {provider}")
    if not api_key or not api_key.strip():
        raise ValueError("API 키가 비어 있습니다.")
    return fn(items, words, dwgno_map, api_key.strip(), on_progress=on_progress)
