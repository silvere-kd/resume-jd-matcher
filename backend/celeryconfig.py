# backend/celeryconfig.py

import os
from kombu import Queue, Exchange

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

# -------- Queues & Routing --------
# Exchanges (direct for simple routing)

default_exchange = Exchange("default", type="direct")
llm_exchange = Exchange("llm", type="direct")
pdf_exchange = Exchange("pdf", type="direct")

# Declare queues
task_queues = (
    Queue("celery", exchange=default_exchange, routing_key="celery"),  # default
    Queue("default", exchange=default_exchange, routing_key="default"),
    Queue("llm", exchange=llm_exchange, routing_key="llm"),
    Queue("pdf", exchange=pdf_exchange, routing_key="pdf"),
)

# Default routing if a task has no explicit route
task_default_queue = "default"
task_default_exchange = "default"
task_default_routing_key = "default"

# We can optionally define task_routes if there is multiple tasks
# Here we keep it minimal and mostly route from apply_async.
task_routes = {
    # Example (for dedicated PDF task):
    # "run_pdf_parse": {"queue": "pdf", "routing_key": "pdf"},
    # Our main agent task can default to llm via apply_async from code.
}
