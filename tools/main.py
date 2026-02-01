from __future__ import annotations

import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse
from fastapi.responses import Response
from tools.exporter import report_to_markdown, report_to_pdf_bytes


from tools.job_manager import JOB_MANAGER
from tools.orchestrator import run_pipeline_with_progress
import math
import numpy as np

def sanitize_json(obj):
    if isinstance(obj, (float, np.floating)):
        return None if (math.isnan(obj) or math.isinf(obj)) else float(obj)
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_json(v) for v in obj]
    return obj

app = FastAPI(title="Jozu Labs Analytics")

UPLOAD_DIR = Path("data/uploads")
REPORT_DIR = Path("data/reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ALLOWED = {".csv", ".xlsx", ".xls"}
ALLOWED = {".csv", ".xlsx", ".xls", ".parquet", ".jsonl", ".ndjson"} # Upgraded


# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")
# Serve generated profiling reports
app.mount("/reports", StaticFiles(directory=str(REPORT_DIR)), name="reports")

EXEC = ThreadPoolExecutor(max_workers=2)

@app.get("/export/{job_id}.md")
def export_markdown(job_id: str):
    job = JOB_MANAGER.get(job_id)
    if not job or not job.done or job.error:
        return JSONResponse({"error": "job not ready"}, status_code=404)
    md = report_to_markdown(job.result or {})
    filename = f"{job_id}.md"
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/export/{job_id}.pdf")
def export_pdf(job_id: str):
    job = JOB_MANAGER.get(job_id)
    if not job or not job.done or job.error:
        return JSONResponse({"error": "job not ready"}, status_code=404)

    # pdf_bytes = report_to_pdf_bytes(job.result or {})
    pdf_bytes = report_to_pdf_bytes(job.result or {}, job_id=job_id)

    filename = f"{job_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.post("/upload_async")
async def upload_async(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED:
        return JSONResponse({"error": "Only CSV/XLSX supported."}, status_code=400)

    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    job = JOB_MANAGER.create_job()

    def on_event(evt: dict):
        JOB_MANAGER.emit(job.id, evt)

    def run():
        try:
            report = run_pipeline_with_progress(str(save_path), file.filename, progress_cb=on_event)
            JOB_MANAGER.set_result(job.id, report)
        except Exception as e:
            JOB_MANAGER.set_error(job.id, str(e))

    EXEC.submit(run)

    return JSONResponse({"job_id": job.id})

@app.get("/progress/{job_id}")
def progress(job_id: str):
    job = JOB_MANAGER.get(job_id)
    if not job:
        return JSONResponse({"error": "job not found"}, status_code=404)

    def event_stream():
        # Send initial hello
        yield "event: hello\ndata: {}\n\n"

        while True:
            try:
                evt = job.queue.get(timeout=1.0)
            except Exception:
                # keep connection alive
                yield "event: ping\ndata: {}\n\n"
                if job.done:
                    break
                continue

            # Server-Sent Events: one event per message
            etype = evt.get("type", "message")
            yield f"event: {etype}\n"
            yield f"data: {json.dumps(evt)}\n\n"

            if evt.get("type") == "done":
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/result/{job_id}")
def result(job_id: str):
    job = JOB_MANAGER.get(job_id)
    if not job:
        return JSONResponse({"error": "job not found"}, status_code=404)
    if not job.done:
        return JSONResponse({"status": "running"}, status_code=202)
    if job.error:
        return JSONResponse({"status": "error", "error": job.error}, status_code=500)

    safe_report = sanitize_json(job.result or {})
    return JSONResponse({"status": "done", "report": safe_report})
