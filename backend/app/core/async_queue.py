# backend/app/core/async_queue.py
import uuid

class AsyncJobQueueDraft:
    """Draft for async job queue. Will later use Celery/RQ."""
    def __init__(self):
        self.jobs = {}

    def submit_job(self, payload: dict) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {"status": "queued", "result": None}
        # In real queue: enqueue the job for background processing
        return job_id
    
    def get_status(self, job_id: str) -> dict:
        return self.jobs.get(job_id, {"status": "not_found", "result": None})
    
# Singleton
queue = AsyncJobQueueDraft()
