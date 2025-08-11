# backend/app/core/async_queue.py

from typing import Optional, Dict, Any
from celery.result import AsyncResult
from backend.app.core.tasks import run_agent_job
from backend.worker.worker import celery_app
from backend.app.models.job_models import JobState

def _map_state(celery_state: str) -> JobState:
    try:
        return JobState(celery_state)
    except ValueError:
        return JobState.UNKNOWN

class AsyncJobQueueCelery:
    """Async job queue using Celery."""
    def submit_job(self, job_type: str, payload: dict) -> str:
        # Ensure we don't pass 'job_type' twice (in task arg and inside payload)
        clean_payload = dict(payload or {})
        clean_payload.pop("job_type", None)
        celery_result = run_agent_job.delay(job_type, clean_payload)
        return celery_result.id
    
    def _get_async_result(self, job_id: str) -> AsyncResult:
        return AsyncResult(job_id, app=celery_app)
    
    def get_status(self, job_id: str) -> dict:
        ar = self._get_async_result(job_id)
        state = _map_state(ar.status)
        info = None
        if ar.info and isinstance(ar.info, dict):
            info = ar.info
        return {"job_id": job_id, "status": state, "info": info}
    
    def get_result(self, job_id:str) -> Dict[str, Any]:
        ar = self._get_async_result(job_id)
        state = _map_state(ar.status)

        if state == JobState.SUCCESS:
            return {"job_id": job_id, "status": state, "result": ar.result, "error": None}
        if state == JobState.FAILURE:
            err = str(ar.result) if ar.result else "Unknown error"
            return {"job_id": job_id, "status": state, "result": None, "error": err}
        
        # Not ready yet
        return {"job_id": job_id, "status": state, "result": None, "error": None}
    
    def wait_for_result(self, job_id:str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Block until job finishes or timeout (seconds).
        Returns same shape as get_result().
        """
        ar = self._get_async_result(job_id)

        try:
            value = ar.get(timeout=timeout, propagate=False) # don't raise exception, capture in .result
        except Exception as e:  # timeout or backend error
            # After timeout, reflect current state
            state = _map_state(ar.status)
            if str(e):
                return {"job_id": job_id, "status": state, "result": None, "error": str(e)}
            return {"job_id": job_id, "status": state, "result": None, "error": "Timeout or retrieval error"}
        
        # After get(), state is terminal or we have a value
        state = _map_state(ar.status)
        if state == JobState.SUCCESS:
            return {"job_id": job_id, "status": state, "result": value, "error": None}
        if state == JobState.FAILURE:
            err = str(ar.result) if ar.result else "Unknown error"
            return {"job_id": job_id, "status": state, "result": None, "error": err}
        return {"job_id": job_id, "status": state, "result": None, "error": None}

    
# Singleton
queue = AsyncJobQueueCelery()
