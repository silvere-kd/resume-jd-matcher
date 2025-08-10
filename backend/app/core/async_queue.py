# backend/app/core/async_queue.py

from celery.result import AsyncResult
from backend.app.core.tasks import run_agent_job
from backend.worker.worker import celery_app

class AsyncJobQueueCelery:
    """Async job queue using Celery."""
    def submit_job(self, job_type: str, payload: dict) -> str:
        # Ensure we don't pass 'job_type' twice (in task arg and inside payload)
        clean_payload = dict(payload or {})
        clean_payload.pop("job_type", None)
        celery_result = run_agent_job.delay(job_type, clean_payload)
        return celery_result.id
    
    def get_status(self, job_id: str) -> dict:
        result = AsyncResult(job_id, app=celery_app)
        status = result.status
        value = result.result if result.successful() else None
        return {"status": status, "result": value}
    
# Singleton
queue = AsyncJobQueueCelery()
