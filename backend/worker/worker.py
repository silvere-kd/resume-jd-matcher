# backend/worker/worker.py

from celery import Celery

# Create Celery app
celery_app = Celery("resume_jd_matcher")
celery_app.config_from_object("backend.celeryconfig")

# Ensure tasks are imported on worker start
import backend.app.core.tasks       # noqa: F401
