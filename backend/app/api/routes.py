#backend/app/api/routes.py

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from fastapi.responses import FileResponse
from celery.result import AsyncResult

from backend.app.core.pdf_parser import PDFParser
from backend.app.core.async_queue import queue
from backend.app.core.artifacts import PDFRenderer
from backend.app.models.job_models import(
    ResumeJDRequest,
    PDFUploadResponse,
    JobSubmitResponse,
    JobStatusResponse,
    JobResultResponse,
)
from backend.worker.worker import celery_app

import tempfile
import os
import json
import datetime


api_router = APIRouter()
_pdf = PDFRenderer()

@api_router.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

@api_router.post("/parse-pdf", response_model=PDFUploadResponse, tags=["Parsing"])
async def parse_pdf_endpoint(file: UploadFile = File(...)):
    """Extract text from uploaded PDF file."""
    content = await file.read()
    parser = PDFParser()
    text = parser.extract_text(content)
    return PDFUploadResponse(extracted_text=text)

@api_router.post("/submit-job", response_model=JobSubmitResponse, tags=["Jobs"])
async def submit_job(request: ResumeJDRequest):
    """Submit a matching/enhancing/cover letter job."""

    jt = (request.job_type or "").lower()
    if jt not in {"match", "enhance", "cover_letter"}:
        raise HTTPException(status_code=422, detail="job_type must be one of: match, enhance, cover_letter")
    job_id = queue.submit_job(jt, request.dict())
    return JobSubmitResponse(job_id=job_id)

@api_router.get("/job-status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def job_status(job_id: str):
    status = queue.get_status(job_id)
    return JobStatusResponse(**status)

@api_router.get("/job/{job_id}", response_model=JobResultResponse, tags=["Jobs"])
async def job_result(job_id:str):
    result = queue.get_result(job_id)
    return JobResultResponse(**result)

@api_router.get("/job-wait/{job_id}", response_model=JobResultResponse, tags=["Jobs"])
async def job_wait(job_id: str, timeout: Optional[float] = Query(default=30.0, ge=0.0, description="Seconds to wait")):
    """
    Blocks up to `timeout` seconds for the result, then returns current state/result.
    Good for Swagger testing or Streamlit 'long poll'.
    """
    result = queue.wait_for_result(job_id, timeout=timeout)
    return JobResultResponse(**result)

# ------------ Warmup endpoints ------------
@api_router.post("/warmup", tags=["Health"])
def warmup():
    """
    Enqueue a warmup task for the active model.
    Returns a task id so we can /job-wait on it if desired.
    """
    async_res = celery_app.send_task("warmup_llm", queue="llm", routing_key="llm")
    return {"job_id": async_res.id}

@api_router.get("/warmup-wait/{job_id}", tags=["Health"])
def warmup_wait(job_id: str, timeout: Optional[float] = Query(default=120.0, ge=0.0)):
    """
    Wait for a specific warmup job to complete.
    """
    ar = AsyncResult(job_id, app=celery_app)
    try:
        val = ar.get(timeout=timeout, propagate=False)
    except Exception as e:
        return {"job_id": job_id, "status": ar.status, "error": str(e)}
    return {"job_id": job_id, "status": ar.status, "result": val}

# ---------------- Downloadable Artifacts ----------------

@api_router.get("/job/{job_id}/download", tags=["Jobs"])
async def job_download(
    job_id: str,
    format: str = Query("md", pattern="^(md|json|pdf)$", description="Download format: md, json, or pdf"),
):
    """
    Download the job's result as a Markdown (md), JSON (json), or PDF (pdf) file.
    """
    jr = queue.get_result(job_id)
    status = jr.get("status")
    raw_result = jr.get("result")

    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if status not in ("SUCCESS", "FAILURE"):
        raise HTTPException(status_code=202, detail=f"Job not finished yet (status={status})")
    if status == "FAILURE":
        err = jr.get("error") or "Unknown error"
        if format == "json":
            return _download_json({"job_id": job_id, "status": status, "error": err}, f"job_{job_id}_error.json")
        raise HTTPException(status_code=500, detail=f"Job failed: {err}")

    # SUCCESS — unwrap nested shapes like {"status":"done","result":{...}}
    result = _unwrap_result(raw_result)

    # Detect job type by keys at the unwrapped level
    if isinstance(result, dict) and "match_score" in result:
        job_type = "match"
        md = _markdown_for_match(result)
        filename_md = f"match_report_{job_id}.md"
        filename_json = f"match_report_{job_id}.json"
        filename_pdf = f"match_report_{job_id}.pdf"
        if format == "json":
            return _download_json({"job_id": job_id, "status": status, "result": result, "job_type": job_type}, filename_json)
        if format == "pdf":
            tmp_path = _tmp_path(filename_pdf)
            _pdf.build_match_pdf(tmp_path, result)
            return FileResponse(tmp_path, media_type="application/pdf", filename=os.path.basename(tmp_path))
        return _download_md(md, filename_md)

    if isinstance(result, dict) and "resume_enhancement_md" in result:
        job_type = "enhance"
        md = _markdown_for_enhance(result)
        filename_md = f"resume_enhancement_{job_id}.md"
        filename_json = f"resume_enhancement_{job_id}.json"
        filename_pdf = f"resume_enhancement_{job_id}.pdf"
        if format == "json":
            return _download_json({"job_id": job_id, "status": status, "result": result, "job_type": job_type}, filename_json)
        if format == "pdf":
            tmp_path = _tmp_path(filename_pdf)
            _pdf.build_enhance_pdf(tmp_path, result)
            return FileResponse(tmp_path, media_type="application/pdf", filename=os.path.basename(tmp_path))
        return _download_md(md, filename_md)

    if isinstance(result, dict) and "cover_letter_md" in result:
        job_type = "cover_letter"
        md = _markdown_for_cover_letter(result)
        filename_md = f"cover_letter_{job_id}.md"
        filename_json = f"cover_letter_{job_id}.json"
        filename_pdf = f"cover_letter_{job_id}.pdf"
        if format == "json":
            return _download_json({"job_id": job_id, "status": status, "result": result, "job_type": job_type}, filename_json)
        if format == "pdf":
            tmp_path = _tmp_path(filename_pdf)
            _pdf.build_cover_letter_pdf(tmp_path, result)
            return FileResponse(tmp_path, media_type="application/pdf", filename=os.path.basename(tmp_path))
        return _download_md(md, filename_md)

    # Unknown structure → generic
    if format == "json":
        return _download_json({"job_id": job_id, "status": status, "result": result, "job_type": "unknown"}, f"job_{job_id}.json")
    if format == "pdf":
        tmp_path = _tmp_path(f"job_{job_id}.pdf")
        pretty = _pretty_json(result)
        _pdf.build_generic_pdf(tmp_path, "Job Result", pretty)
        return FileResponse(tmp_path, media_type="application/pdf", filename=os.path.basename(tmp_path))
    md = _markdown_from_unknown(result)
    return _download_md(md, f"job_{job_id}.md")

# ---------------- Helpers: Markdown & File responses ----------------

def _unwrap_result(raw_result: Any) -> Any:
    """
    Accepts any structure. If it's a dict that looks like {'status': 'done', 'result': {...}},
    return the inner .result; otherwise return as-is.
    """
    if isinstance(raw_result, dict) and "result" in raw_result and set(raw_result.keys()) <= {"status", "result"}:
        return raw_result.get("result")
    return raw_result

def _download_md(markdown_text: str, filename: str) -> FileResponse:
    tmp_path = _write_temp_file(markdown_text, filename)
    return FileResponse(tmp_path, media_type="text/markdown", filename=os.path.basename(tmp_path))

def _download_json(payload: Dict[str, Any], filename: str) -> FileResponse:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    tmp_path = _write_temp_file(text, filename)
    return FileResponse(tmp_path, media_type="application/json", filename=os.path.basename(tmp_path))

def _write_temp_file(content: str, filename: str) -> str:
    tmp_path = _tmp_path(filename)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    return tmp_path

def _tmp_path(filename: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="artifacts_")
    return os.path.join(tmp_dir, filename)

def _header(title: str) -> str:
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"# {title}\n\n_Generated: {now}_\n\n"

def _pretty_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except Exception:
        return str(value)

def _markdown_for_match(result: Dict[str, Any]) -> str:
    score = result.get("match_score", "N/A")
    strengths: List[str] = result.get("strengths", []) or []
    gaps: List[str] = result.get("gaps", []) or []
    summary = result.get("summary", "")

    md = _header("Resume ↔ JD Match Report")
    md += f"## Overall Score\n**{score}%**\n\n"
    md += "## Strengths\n"
    md += "\n".join(f"- {s}" for s in strengths) + ("\n\n" if strengths else "_None_\n\n")
    md += "## Gaps\n"
    md += "\n".join(f"- {g}" for g in gaps) + ("\n\n" if gaps else "_None_\n\n")
    md += "## Summary\n"
    md += f"{summary or '_No summary provided._'}\n"
    return md

def _markdown_for_enhance(result: Dict[str, Any]) -> str:
    body = result.get("resume_enhancement_md", "") or "_No suggestions generated._"
    md = _header("Resume Enhancement Suggestions")
    md += body
    return md

def _markdown_for_cover_letter(result: Dict[str, Any]) -> str:
    body = result.get("cover_letter_md", "") or "_No cover letter generated._"
    md = _header("Cover Letter")
    md += body
    return md

def _markdown_from_unknown(result_any: Any) -> str:
    md = _header("Job Result")
    md += "```\n" + _pretty_json(result_any) + "\n```"
    return md
