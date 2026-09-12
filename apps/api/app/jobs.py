"""Job storage and pipeline orchestration.

Kept deliberately simple for an internal team tool: each job is a folder on
disk (`DATA_DIR/jobs/<id>/`) with its input/output files and a status.json.
No database — a few concurrent users don't need one, and this is one less
moving part to deploy/operate. Swap in Postgres/SQLite later if usage grows.
"""
import json
import os
import traceback
import uuid
from datetime import datetime, timezone

from . import checklist, providers, report
from .drawing import detect_drawing_numbers, extract_words, page_count
from .mark import mark

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
JOBS_DIR = os.path.join(DATA_DIR, "jobs")


def _job_dir(job_id: str) -> str:
    return os.path.join(JOBS_DIR, job_id)


def _status_path(job_id: str) -> str:
    return os.path.join(_job_dir(job_id), "status.json")


def _read_status(job_id: str) -> dict | None:
    path = _status_path(job_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_status(job_id: str, status: dict):
    with open(_status_path(job_id), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def create_job(drawing_filename: str, drawing_bytes: bytes,
                checklist_files: list[tuple[str, bytes]]) -> str:
    job_id = uuid.uuid4().hex[:12]
    d = _job_dir(job_id)
    os.makedirs(os.path.join(d, "checklists"), exist_ok=True)
    os.makedirs(os.path.join(d, "output"), exist_ok=True)

    with open(os.path.join(d, "drawing.pdf"), "wb") as f:
        f.write(drawing_bytes)

    checklist_paths = []
    for i, (name, content) in enumerate(checklist_files):
        safe_name = f"{i}_{os.path.basename(name)}"
        path = os.path.join(d, "checklists", safe_name)
        with open(path, "wb") as f:
            f.write(content)
        checklist_paths.append(path)

    _write_status(job_id, {
        "id": job_id,
        "drawing_filename": drawing_filename,
        "checklist_paths": checklist_paths,
        "status": "queued",
        "step_detail": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    })
    return job_id


def get_job(job_id: str) -> dict | None:
    return _read_status(job_id)


def list_jobs() -> list[dict]:
    if not os.path.isdir(JOBS_DIR):
        return []
    jobs = []
    for job_id in os.listdir(JOBS_DIR):
        s = _read_status(job_id)
        if s:
            jobs.append(s)
    jobs.sort(key=lambda j: j["created_at"], reverse=True)
    return jobs


def _update(job_id: str, **kwargs):
    s = _read_status(job_id)
    s.update(kwargs)
    _write_status(job_id, s)


def run_job(job_id: str, provider: str, api_key: str):
    d = _job_dir(job_id)
    drawing_path = os.path.join(d, "drawing.pdf")
    s = _read_status(job_id)

    try:
        _update(job_id, status="extracting", step_detail="도면 텍스트 추출 중")
        words = extract_words(drawing_path)
        n_pages = page_count(drawing_path)
        dwgno_map = detect_drawing_numbers(words, n_pages)

        checklist_bytes = []
        for p in s["checklist_paths"]:
            with open(p, "rb") as f:
                checklist_bytes.append((os.path.basename(p), f.read()))

        items = checklist.parse_checklist_files(checklist_bytes)
        if not items:
            items = list(checklist.DEFAULT_ITEMS)
        # always include the standard QC categories regardless of an uploaded law checklist
        if not any(it["source"].startswith("기본(QC)") for it in items):
            items = items + [it for it in checklist.DEFAULT_ITEMS if it["source"] == "기본(QC)"]

        _update(job_id, status="reviewing", step_detail=f"AI 검토 중 (항목 {len(items)}건)")
        reviewed = providers.run_review(provider, items, words, dwgno_map, api_key)

        _update(job_id, status="marking", step_detail="도면에 마킹하는 중")
        mark_entries = [
            {**r, "color": "red" if r["result"] == "error" else "blue"}
            for r in reviewed if r["result"] != "n/a"
        ]
        marked_path = os.path.join(d, "output", "marked.pdf")
        mark(drawing_path, mark_entries, marked_path)

        final_path = os.path.join(d, "output", "marked_final.pdf")
        report.insert_index_page(marked_path, reviewed, final_path)

        xlsx_path = os.path.join(d, "output", "checklist.xlsx")
        report.build_excel(reviewed, xlsx_path)

        _update(
            job_id,
            status="done",
            step_detail=None,
            result={
                "marked_pdf_url": f"/jobs/{job_id}/files/marked_final.pdf",
                "excel_url": f"/jobs/{job_id}/files/checklist.xlsx",
                "summary": report.summary_rows_for_web(reviewed),
            },
        )
    except Exception as e:
        _update(job_id, status="error", error=f"{e}", step_detail=None)
        traceback.print_exc()
