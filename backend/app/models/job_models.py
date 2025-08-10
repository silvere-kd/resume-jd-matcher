
#backend/app/models/job_models.py

from pydantic import BaseModel, Field
from typing import Optional, Dict

class ResumeJDRequest(BaseModel):
    job_type: str = Field(..., description="One of: match, enhance, cover_letter")
    resume: Optional[str] = Field(default=None, description="Plain text resume")
    jd: Optional[str] = Field(default=None, description="Plain text job description")

class PDFUploadResponse(BaseModel):
    extracted_text: str

class JobSubmitResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    status: str
    result: Optional[Dict] = None
