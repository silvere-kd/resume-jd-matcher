# backend/worker/worker.py

from celery import Celery

celery_app = Celery("resume_jd_matcher")
celery_app.config_from_object("backend.celeryconfig")

import backend.app.core.tasks  # Ensure all tasks are registered
