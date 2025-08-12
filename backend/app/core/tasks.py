# backend/app/core/tasks.py

from celery.utils.log import get_task_logger
from backend.worker.worker import celery_app
from backend.app.core.agent_orchestrator import AgentOrchestrator
from backend.app.config import settings

logger = get_task_logger(__name__)

@celery_app.task(
    name="run_agent_job",
    bind=False,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 1},    # fewer retries to avoid duplicate long runs
    soft_time_limit=settings.CELERY_SOFT_TIME_LIMIT,  #  600s
    time_limit=settings.CELERY_HARD_TIME_LIMIT,       #  660s
    acks_late=False,                          # ack immediately; or set True with care + visibility_timeout
)
def run_agent_job(job_type: str, data: dict):
    logger.info("Starting job type=%s", job_type)
    orchestrator = AgentOrchestrator()
    result = orchestrator.run(job_type, data or {})
    logger.info("Finished job type=%s", job_type)
    return result
