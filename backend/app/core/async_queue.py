# backend/app/core/async_queue.py
from backend.app.core.tasks import run_agent_job

class AsyncJobQueueCelery:
    """Async job queue using Celery."""
    def submit_job(self, job_type: str, payload: dict) -> str:
        celery_result = run_agent_job.delay(job_type, payload)
        return celery_result.id
    
    def get_status(self, job_id: str) -> dict:
        from celery.result import AsyncResult
        from backend.worker.worker import celery_app
        result = AsyncResult(job_id, app=celery_app)
        status = result.status
        value = result.result if result.successful() else None
        return {"status": status, "result": value}
    
# Singleton
queue = AsyncJobQueueCelery()
