# backend/app/core/async_queue.py

from typing import Dict, Any
from celery.result import AsyncResult
from backend.app.core.tasks import run_agent_job
from backend.worker.worker import celery_app

class AsyncJobQueueCelery:
    """Async job queue using Celery with queue routing."""

    def _pick_queue(self, job_type: str, payload: Dict[str, Any]) -> str:
        """
        Decide which queue to use based on job_type/payload.
        - LLM-heavy jobs → 'llm'
        - Future: add 'pdf' for large PDF parse tasks, etc.
        """
        jt = (job_type or "").lower()
        if jt in {"match", "enhance", "cover_letter"}:
            return "llm"
        return "default"
    
    def submit_job(self, job_type: str, payload: dict) -> str:
        # Ensure we don't pass 'job_type' twice (in task arg and inside payload)
        clean_payload = dict(payload or {})
        clean_payload.pop("job_type", None)

        queue_name = self._pick_queue(job_type, clean_payload)

        # Route to the selected queue via apply_async; use positional args
        async_result = run_agent_job.apply_async(
            args=[job_type, clean_payload],
            queue=queue_name,
            routing_key=queue_name,
        )
        return async_result.id    
    
    def get_status(self, job_id: str) -> Dict[str, Any]:
        result = AsyncResult(job_id, app=celery_app)
        status = result.status
        value = result.result if result.successful() else None
        return {"job_id": job_id, "status": status, "info": None}
    
    def get_result(self, job_id: str) -> Dict[str, Any]:
        result = AsyncResult(job_id, app=celery_app)
        state = result.status
        if state == "SUCCESS":
            return {"job_id": job_id, "status": state, "result": result.result, "error": None}
        if state == "FAILURE":
            return {"job_id": job_id, "status": state, "result": None, "error": str(result.result)}
        return {"job_id": job_id, "status": state, "result": None, "error": None}
        
    
    def wait_for_result(self, job_id:str, timeout: float | None = None) -> Dict[str, Any]:
        """
        Block until job finishes or timeout (seconds).
        Returns same shape as get_result().
        """
        ar = AsyncResult(job_id, app=celery_app)
        try:
            val = ar.get(timeout=timeout, propagate=False)
        except Exception as e:
            state = ar.status
            return {"job_id": job_id, "status": state, "result": None, "error": str(e) if str(e) else "Timeout"}
        state = ar.status
        if state == "SUCCESS":
            return {"job_id": job_id, "status": state, "result": val, "error": None}
        if state == "FAILURE":
            return {"job_id": job_id, "status": state, "result": None, "error": str(ar.result)}
        return {"job_id": job_id, "status": state, "result": None, "error": None}

    
# Singleton
queue = AsyncJobQueueCelery()
