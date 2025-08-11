# frontend/api_client.py

import os
import time
from typing import Optional, Dict, Any
import requests

class BackendClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.base_url = (base_url or os.getenv("BACKEND_URL") or "http://localhost:8000").rstrip("/")
        self.timeout = timeout

    # -------- Parsing --------
    def parse_pdf(self, file_bytes: bytes, filename: str = "resume.pdf") -> str:
        url = f"{self.base_url}/parse-pdf"
        files = {"file": (filename, file_bytes, "application/pdf")}
        resp = requests.post(url, files=files, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("extracted_text", "") or ""

    # -------- Jobs --------
    def submit_job(self, job_type: str, resume: str, jd: str) -> str:
        url = f"{self.base_url}/submit-job"
        payload = {"job_type": job_type, "resume": resume, "jd": jd}
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["job_id"]

    def job_status(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/job-status/{job_id}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def job_result(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/job/{job_id}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def job_wait(self, job_id: str, timeout: float = 60.0) -> Dict[str, Any]:
        url = f"{self.base_url}/job-wait/{job_id}"
        params = {"timeout": timeout}
        resp = requests.get(url, params=params, timeout=timeout + 5)
        resp.raise_for_status()
        return resp.json()

    # -------- Convenience: poll with progress callback --------
    def wait_with_progress(
        self,
        job_id: str,
        total_wait: float = 120.0,
        poll_interval: float = 1.5,
        on_tick=None,
    ) -> Dict[str, Any]:
        elapsed = 0.0
        while elapsed < total_wait:
            try:
                res = self.job_result(job_id)
            except Exception as e:
                res = {"status": "UNKNOWN", "error": str(e)}
            if on_tick:
                on_tick(elapsed, res.get("status"))
            if res.get("status") in ("SUCCESS", "FAILURE"):
                return res
            time.sleep(poll_interval)
            elapsed += poll_interval
        # Fallback: final status fetch
        return self.job_result(job_id)
