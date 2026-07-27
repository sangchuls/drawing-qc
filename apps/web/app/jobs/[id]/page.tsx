"use client";

import { use, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

type SummaryRow = {
  source: string;
  law: string;
  field: string;
  result: "pass" | "check" | "n/a";
  dwgno: string;
};

type JobDetail = {
  id: string;
  drawing_filename: string;
  status: "queued" | "extracting" | "reviewing" | "marking" | "done" | "error";
  error: string | null;
  step_detail: string | null;
  result: {
    marked_pdf_url: string;
    excel_url: string;
    summary: SummaryRow[];
  } | null;
};

const STATUS_LABEL: Record<string, string> = {
  queued: "대기 중",
  extracting: "도면 텍스트 추출 중",
  reviewing: "AI 검토 중 (체크리스트 항목별 근거 검색)",
  marking: "도면에 마킹하는 중",
  done: "완료",
  error: "오류",
};

const RESULT_LABEL: Record<string, string> = { pass: "확인", check: "미확인", "n/a": "해당없음" };
const RESULT_COLOR: Record<string, string> = {
  pass: "text-blue-600",
  check: "text-amber-600",
  "n/a": "text-neutral-400",
};

export default function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    async function poll() {
      try {
        const res = await fetch(`${API_BASE}/jobs/${id}`);
        if (!res.ok) throw new Error("작업 정보를 불러오지 못했습니다.");
        const data: JobDetail = await res.json();
        if (stop) return;
        setJob(data);
        if (data.status !== "done" && data.status !== "error") {
          setTimeout(poll, 2500);
        }
      } catch (e) {
        if (!stop) setError(e instanceof Error ? e.message : "오류가 발생했습니다.");
      }
    }
    poll();
    return () => {
      stop = true;
    };
  }, [id]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <a href="/jobs" className="text-sm text-neutral-500 underline hover:text-neutral-900">
        ← 작업 목록
      </a>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {!job && !error && <p className="mt-4 text-sm text-neutral-500">불러오는 중...</p>}

      {job && (
        <div className="mt-4">
          <h1 className="text-xl font-semibold">{job.drawing_filename}</h1>

          {job.status !== "done" && job.status !== "error" && (
            <div className="mt-4 flex items-center gap-2 text-sm text-neutral-600">
              <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
              {STATUS_LABEL[job.status]}
              {job.step_detail && <span className="text-neutral-400">— {job.step_detail}</span>}
            </div>
          )}

          {job.status === "error" && (
            <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
              검토 중 오류가 발생했습니다: {job.error}
            </p>
          )}

          {job.status === "done" && job.result && (
            <div className="mt-6 space-y-6">
              <div className="flex gap-3">
                <a
                  href={job.result.marked_pdf_url}
                  className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white dark:bg-neutral-100 dark:text-neutral-900"
                >
                  마킹된 도면 PDF 다운로드
                </a>
                <a
                  href={job.result.excel_url}
                  className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium dark:border-neutral-700"
                >
                  체크리스트 Excel 다운로드
                </a>
              </div>

              <div>
                <h2 className="mb-2 text-sm font-semibold text-neutral-700 dark:text-neutral-300">
                  항목별 근거 도면번호 ({job.result.summary.length}건)
                </h2>
                <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-neutral-50 text-xs text-neutral-500 dark:bg-neutral-900">
                      <tr>
                        <th className="px-3 py-2">법령/체크항목</th>
                        <th className="px-3 py-2">결과</th>
                        <th className="px-3 py-2">근거 도면번호</th>
                      </tr>
                    </thead>
                    <tbody>
                      {job.result.summary.map((row, i) => (
                        <tr key={i} className="border-t border-neutral-100 dark:border-neutral-800">
                          <td className="px-3 py-2">
                            <div>{row.law}</div>
                            <div className="text-xs text-neutral-400">{row.field}</div>
                          </td>
                          <td className={`px-3 py-2 font-medium ${RESULT_COLOR[row.result]}`}>
                            {RESULT_LABEL[row.result]}
                          </td>
                          <td className="px-3 py-2">{row.dwgno}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
