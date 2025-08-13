# backend/worker/worker.py

from celery import Celery
from celery.signals import worker_ready
from backend.app.config import settings

# Create Celery app
celery_app = Celery("resume_jd_matcher")
celery_app.config_from_object("backend.celeryconfig")

# Ensure tasks are imported on worker start
import backend.app.core.tasks       # noqa: F401

@worker_ready.connect
def _warmup_on_ready(sender=None, **kwargs):
    """
    When the worker starts, auto-warm the active LLM model.
    Only the LLM queue worker should do this (to avoid warming multiple times).
    """
    if not settings.WARMUP_ENABLED:
        return
    # Send to llm queue so it runs on the right worker
    try:
        celery_app.send_task("warmup_llm", queue="llm", routing_key="llm")
    except Exception:
        # If routing not set or worker not bound to llm, still try default
        celery_app.send_task("warmup_llm")
