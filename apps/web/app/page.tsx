"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PROVIDERS, ProviderId, loadKeys, loadSelectedProvider, saveKey, saveSelectedProvider } from "../lib/apiKeys";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export default function HomePage() {
  const router = useRouter();
  const [drawing, setDrawing] = useState<File | null>(null);
  const [checklists, setChecklists] = useState<FileList | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<ProviderId>("anthropic");
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    const saved = loadSelectedProvider();
    setProvider(saved);
    setApiKey(loadKeys()[saved] ?? "");
  }, []);

  function onProviderChange(id: ProviderId) {
    setProvider(id);
    saveSelectedProvider(id);
    setApiKey(loadKeys()[id] ?? "");
  }

  function onApiKeyChange(value: string) {
    setApiKey(value);
    saveKey(provider, value);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!drawing) {
      setError("도면 PDF를 선택해 주세요.");
      return;
    }
    if (!apiKey.trim()) {
      setError("선택한 LLM 제공자의 API 키를 입력해 주세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const tokenRes = await fetch("/api/upload-token", { method: "POST" });
      if (!tokenRes.ok) throw new Error("업로드 인증에 실패했습니다.");
      const { token } = await tokenRes.json();

      const form = new FormData();
      form.append("token", token);
      form.append("provider", provider);
      form.append("api_key", apiKey.trim());
      form.append("drawing", drawing);
      if (checklists) {
        for (const f of Array.from(checklists)) form.append("checklists", f);
      }

      const res = await fetch(`${API_BASE}/jobs`, { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "업로드에 실패했습니다.");
      }
      const { job_id } = await res.json();
      router.push(`/jobs/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">도면 QC 검토</h1>
          <p className="mt-1 text-sm text-neutral-500">
            건축 도면과 법규/QC 체크리스트를 올리면 근거 위치를 찾아 마킹한 도면과 체크리스트 리포트를 만들어 줍니다.
          </p>
        </div>
        <nav className="text-sm">
          <a href="/jobs" className="text-neutral-500 underline hover:text-neutral-900">
            이전 작업 목록
          </a>
        </nav>
      </header>

      <form onSubmit={onSubmit} className="space-y-6 rounded-xl border border-neutral-200 p-6 dark:border-neutral-800">
        <div className="grid gap-4 rounded-lg bg-neutral-50 p-4 dark:bg-neutral-900">
          <div>
            <label className="mb-1 block text-sm font-medium">LLM 제공자</label>
            <select
              value={provider}
              onChange={(e) => onProviderChange(e.target.value as ProviderId)}
              className="block w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-950"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">API 키</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => onApiKeyChange(e.target.value)}
              placeholder="sk-..."
              autoComplete="off"
              className="block w-full rounded-md border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-950"
            />
            <p className="mt-1 text-xs text-neutral-500">
              이 브라우저에만 제공자별로 개별 저장됩니다. 서버에는 저장되지 않고, 검토 요청 시에만 전달됩니다.
            </p>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">도면 PDF (필수)</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setDrawing(e.target.files?.[0] ?? null)}
            className="block w-full text-sm"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">체크리스트 (선택, PDF/Excel 여러 개 가능)</label>
          <input
            type="file"
            multiple
            accept="application/pdf,.xlsx,.xls"
            onChange={(e) => setChecklists(e.target.files)}
            className="block w-full text-sm"
          />
          <p className="mt-1 text-xs text-neutral-500">
            체크리스트를 올리지 않으면 기본 항목(피난거리·복도폭·방화구획·주차대수 등)으로 검토합니다.
          </p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
        >
          {busy ? "업로드 중..." : "검토 시작"}
        </button>
      </form>
    </div>
  );
}
