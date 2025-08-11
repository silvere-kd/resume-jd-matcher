
#backend/app/models/job_models.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum

class JobState(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    RETRY = "RETRY"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"

class ResumeJDRequest(BaseModel):
    job_type: str = Field(..., description="One of: match, enhance, cover_letter")
    resume: Optional[str] = Field(default=None, description="Plain text resume")
    jd: Optional[str] = Field(default=None, description="Plain text job description")

class PDFUploadResponse(BaseModel):
    extracted_text: str

class JobSubmitResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobState
    info: Optional[Dict[str, Any]] = None

class JobResultResponse(BaseModel):
    job_id: str
    status: JobState
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
