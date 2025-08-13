# backend/app/core/tasks.py

from celery.utils.log import get_task_logger
from backend.worker.worker import celery_app
from backend.app.core.agent_orchestrator import AgentOrchestrator
from backend.app.config import settings
import litellm

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


@celery_app.task(
    name="warmup_llm",
    bind=False,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 0}, 
    soft_time_limit=180, 
    time_limit=240,
)
def warmup_llm():
    """
    Pre-load the model into memory via a tiny LiteLLM call.
    """
    model_id = settings.full_model_id()
    logger.info("Warming up LLM model_id=%s base_url=%s", model_id, settings.LLM_BASE_URL)

    resp = litellm.completion(
        model=model_id,
        api_base=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        timeout=settings.LLM_REQUEST_TIMEOUT,
        messages=[{"role": "user", "content": settings.WARMUP_PROMPT}],
        temperature=0.0,
        max_tokens=16,
    )
    # It will returns a dict-like object; we just log short content
    try:
        txt = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        txt = str(resp)
    logger.info("Warmup response (truncated): %s", (txt or "")[:120])
    return {"status": "ok", "model": model_id}
