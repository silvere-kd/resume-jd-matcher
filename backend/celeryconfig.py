# backend/celeryconfig.py

import os

# redis is in another docker container
# if it's not the case for you,
# use : "redis://localhost:6379/0"

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://host.docker.internal:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

broker_url = BROKER_URL
result_backend = RESULT_BACKEND


task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

# Optional routing example (future: create dedicated queues)
task_queues = None
