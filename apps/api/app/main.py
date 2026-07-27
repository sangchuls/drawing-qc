import os

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import jobs
from .token_auth import verify_upload_token

app = FastAPI(title="도면 QC API")

origins = os.environ.get("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_DRAWING_MB = int(os.environ.get("MAX_DRAWING_MB", "150"))


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    token: str = Form(...),
    drawing: UploadFile = File(...),
    checklists: list[UploadFile] = File(default=[]),
):
    if not verify_upload_token(token):
        raise HTTPException(status_code=401, detail="업로드 인증 토큰이 유효하지 않습니다.")

    drawing_bytes = await drawing.read()
    if len(drawing_bytes) > MAX_DRAWING_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"도면 파일이 {MAX_DRAWING_MB}MB 제한을 초과합니다.")
    if not drawing.filename or not drawing.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="도면은 PDF 파일이어야 합니다.")

    checklist_files = []
    for f in checklists:
        checklist_files.append((f.filename or "checklist", await f.read()))

    job_id = jobs.create_job(drawing.filename, drawing_bytes, checklist_files)
    background_tasks.add_task(jobs.run_job, job_id)
    return {"job_id": job_id}


@app.get("/jobs")
def list_jobs():
    return [
        {"id": j["id"], "drawing_filename": j["drawing_filename"],
         "status": j["status"], "created_at": j["created_at"]}
        for j in jobs.list_jobs()
    ]


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return job


@app.get("/jobs/{job_id}/files/{filename}")
def get_job_file(job_id: str, filename: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    safe_name = os.path.basename(filename)
    path = os.path.join(jobs._job_dir(job_id), "output", safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return FileResponse(path, filename=safe_name)
