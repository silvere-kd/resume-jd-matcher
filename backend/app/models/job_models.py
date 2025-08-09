
#backend/app/models/job_models.py

from pydantic import BaseModel
from typing import Optional

class ResumeJDRequest(BaseModel):
    resume: Optional[str] = None
    jd: Optional[str] = None

class PDFUploadResponse(BaseModel):
    extracted_text: str

class JobSubmitResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    status: str
    result: Optional[str] = None
