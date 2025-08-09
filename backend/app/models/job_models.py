
#backend/app/models/job_models.py

from pydantic import BaseModel
from typing import Optional, Dict

class ResumeJDRequest(BaseModel):
    resume: Optional[str] = None
    jd: Optional[str] = None
    job_type: str

class PDFUploadResponse(BaseModel):
    extracted_text: str

class JobSubmitResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    status: str
    result: Optional[Dict] = None
