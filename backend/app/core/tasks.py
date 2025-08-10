# backend/app/core/tasks.py

from celery.utils.log import get_task_logger
from backend.worker.worker import celery_app
from backend.app.core.agent_orchestrator import AgentOrchestrator

logger = get_task_logger(__name__)

@celery_app.task(
    name="run_agent_job",
    bind=False,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=180,  # seconds
    time_limit=240        # hard limit)
)
def run_agent_job(job_type: str, data: dict):
    logger.info("Starting job type=%s", job_type)
    orchestrator = AgentOrchestrator()
    result = orchestrator.run(job_type, data or {})
    logger.info("Finished job type=%s", job_type)
    return result
