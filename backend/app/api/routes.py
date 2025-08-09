#backend/app/api/routes.py

from fastapi import APIRouter, File, UploadFile
from backend.app.core.pdf_parser import PDFParser
from backend.app.core.async_queue import queue
from backend.app.models.job_models import(
    ResumeJDRequest,
    PDFUploadResponse,
    JobSubmitResponse,
    JobStatusResponse
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
    try:
        text = parser.extract_text(content)
        return PDFUploadResponse(extracted_text=text)
    except Exception as e:
        return PDFUploadResponse(extracted_text=f"Error: {str(e)}")

@api_router.post("/submit-job", response_model=JobSubmitResponse, tags=["Jobs"])
async def submit_job(request: ResumeJDRequest):
    """Submit a matching/enhancing/cover letter job."""
    job_id = queue.submit_job(request.dict())
    return JobSubmitResponse(job_id=job_id)

@api_router.get("/job-status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def job_status(job_id: str):
    status = queue.get_status(job_id)
    return JobStatusResponse(**status)
