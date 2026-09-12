"use client";

// LLM API 키는 서버에 저장하지 않고 각자의 브라우저(localStorage)에만 개별 저장합니다.
// 검토 요청 시에만 백엔드로 전달되어 그 자리에서 사용됩니다.

export const PROVIDERS = [
  { id: "anthropic", label: "Claude (Anthropic)" },
  { id: "openai", label: "GPT (OpenAI)" },
  { id: "google", label: "Gemini (Google)" },
  { id: "xai", label: "Grok (xAI)" },
] as const;

export type ProviderId = (typeof PROVIDERS)[number]["id"];

const KEYS_STORAGE_KEY = "qc:apiKeys";
const PROVIDER_STORAGE_KEY = "qc:selectedProvider";

export function loadKeys(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(KEYS_STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

export function saveKey(provider: ProviderId, apiKey: string) {
  const keys = loadKeys();
  keys[provider] = apiKey;
  localStorage.setItem(KEYS_STORAGE_KEY, JSON.stringify(keys));
}

export function loadSelectedProvider(): ProviderId {
  const saved = localStorage.getItem(PROVIDER_STORAGE_KEY);
  return (PROVIDERS.some((p) => p.id === saved) ? saved : "anthropic") as ProviderId;
}

export function saveSelectedProvider(provider: ProviderId) {
  localStorage.setItem(PROVIDER_STORAGE_KEY, provider);
}
