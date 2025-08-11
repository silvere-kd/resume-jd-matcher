#backend/app/api/routes.py

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from backend.app.core.pdf_parser import PDFParser
from backend.app.core.async_queue import queue
from backend.app.models.job_models import(
    ResumeJDRequest,
    PDFUploadResponse,
    JobSubmitResponse,
    JobStatusResponse,
    JobResultResponse,
)
import tempfile
import os
import json
import datetime


api_router = APIRouter()

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

# ---------------- Downloadable Artifacts ----------------

@api_router.get("/job/{job_id}/download", tags=["Jobs"])
async def job_download(
    job_id: str,
    format: str = Query("md", pattern="^(md|json)$", description="Download format: md or json"),
):
    """
    Download the job's result as a Markdown file (md) or raw JSON (json).
    """
    # Fetch result (non-blocking)
    jr = queue.get_result(job_id)
    status = jr.get("status")
    result = jr.get("result")

    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if status not in ("SUCCESS", "FAILURE"):
        raise HTTPException(status_code=202, detail=f"Job not finished yet (status={status})")
    if status == "FAILURE":
        err = jr.get("error") or "Unknown error"
        # Return error as JSON file if requested
        if format == "json":
            return _download_json({"job_id": job_id, "status": status, "error": err}, f"job_{job_id}_error.json")
        raise HTTPException(status_code=500, detail=f"Job failed: {err}")

    # SUCCESS
    if not isinstance(result, dict):
        # unexpected shape; just dump it as text/JSON
        if format == "json":
            return _download_json({"job_id": job_id, "status": status, "result": result}, f"job_{job_id}.json")
        md = _markdown_from_unknown(result)
        return _download_md(md, f"job_{job_id}.md")

    # Heuristic: detect job type by keys in result payload
    if "match_score" in result:
        job_type = "match"
        md = _markdown_for_match(result)
        filename_md = f"match_report_{job_id}.md"
        filename_json = f"match_report_{job_id}.json"
    elif "resume_enhancement_md" in result:
        job_type = "enhance"
        md = _markdown_for_enhance(result)
        filename_md = f"resume_enhancement_{job_id}.md"
        filename_json = f"resume_enhancement_{job_id}.json"
    elif "cover_letter_md" in result:
        job_type = "cover_letter"
        md = _markdown_for_cover_letter(result)
        filename_md = f"cover_letter_{job_id}.md"
        filename_json = f"cover_letter_{job_id}.json"
    else:
        job_type = "unknown"
        md = _markdown_from_unknown(result)
        filename_md = f"job_{job_id}.md"
        filename_json = f"job_{job_id}.json"

    if format == "json":
        return _download_json({"job_id": job_id, "status": status, "result": result, "job_type": job_type}, filename_json)
    return _download_md(md, filename_md)

# ---------------- Helpers: Markdown & File responses ----------------

def _download_md(markdown_text: str, filename: str) -> FileResponse:
    tmp_path = _write_temp_file(markdown_text, filename)
    return FileResponse(tmp_path, media_type="text/markdown", filename=os.path.basename(tmp_path))

def _download_json(payload: Dict[str, Any], filename: str) -> FileResponse:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    tmp_path = _write_temp_file(text, filename)
    return FileResponse(tmp_path, media_type="application/json", filename=os.path.basename(tmp_path))

def _write_temp_file(content: str, filename: str) -> str:
    # Use a secure temp dir
    tmp_dir = tempfile.mkdtemp(prefix="artifacts_")
    tmp_path = os.path.join(tmp_dir, filename)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    return tmp_path

def _header(title: str) -> str:
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"# {title}\n\n_Generated: {now}_\n\n"

def _markdown_for_match(result: Dict[str, Any]) -> str:
    score = result.get("match_score", "N/A")
    strengths: List[str] = result.get("strengths", []) or []
    gaps: List[str] = result.get("gaps", []) or []
    summary = result.get("summary", "")

    md = _header("Resume ↔ JD Match Report")
    md += f"## Overall Score\n**{score}%**\n\n"
    md += "## Strengths\n"
    md += "\n".join(f"- {s}" for s in strengths) + ("\n" if strengths else "_None_\n")
    md += "\n## Gaps\n"
    md += "\n".join(f"- {g}" for g in gaps) + ("\n" if gaps else "_None_\n")
    md += "\n## Summary\n"
    md += f"{summary or '_No summary provided._'}\n"
    return md

def _markdown_for_enhance(result: Dict[str, Any]) -> str:
    body = result.get("resume_enhancement_md", "")
    md = _header("Resume Enhancement Suggestions")
    # Body is already Markdown; append directly
    md += body if body else "_No suggestions generated._\n"
    return md

def _markdown_for_cover_letter(result: Dict[str, Any]) -> str:
    body = result.get("cover_letter_md", "")
    md = _header("Cover Letter")
    md += body if body else "_No cover letter generated._\n"
    return md

def _markdown_from_unknown(result_any: Any) -> str:
    md = _header("Job Result")
    try:
        md += "```\n" + json.dumps(result_any, indent=2, ensure_ascii=False) + "\n```"
    except Exception:
        md += "```\n" + str(result_any) + "\n```"
    return md
