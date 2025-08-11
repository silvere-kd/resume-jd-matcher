#backend/app/api/routes.py

from typing import Optional
from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from backend.app.core.pdf_parser import PDFParser
from backend.app.core.async_queue import queue
from backend.app.models.job_models import(
    ResumeJDRequest,
    PDFUploadResponse,
    JobSubmitResponse,
    JobStatusResponse,
    JobResultResponse,
)


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
