"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

type JobSummary = {
  id: string;
  drawing_filename: string;
  status: string;
  created_at: string;
};

const STATUS_LABEL: Record<string, string> = {
  queued: "대기 중",
  extracting: "도면 텍스트 추출 중",
  reviewing: "AI 검토 중",
  marking: "도면 마킹 중",
  done: "완료",
  error: "오류",
};

export default function JobsListPage() {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/jobs`)
      .then((r) => {
        if (!r.ok) throw new Error("작업 목록을 불러오지 못했습니다.");
        return r.json();
      })
      .then(setJobs)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">이전 작업 목록</h1>
        <a href="/" className="text-sm text-neutral-500 underline hover:text-neutral-900">
          새 검토 시작
        </a>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!jobs && !error && <p className="text-sm text-neutral-500">불러오는 중...</p>}
      {jobs && jobs.length === 0 && <p className="text-sm text-neutral-500">아직 작업이 없습니다.</p>}

      <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
        {jobs?.map((j) => (
          <li key={j.id} className="py-3">
            <a href={`/jobs/${j.id}`} className="flex items-center justify-between hover:underline">
              <span className="text-sm">{j.drawing_filename}</span>
              <span className="text-xs text-neutral-500">{STATUS_LABEL[j.status] ?? j.status}</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
