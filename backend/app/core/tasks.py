# backend/app/core/tasks.py

from backend.worker.worker import celery_app
from backend.app.core.agent_orchestrator import AgentOrchestrator

@celery_app.task(name="run_agent_job")
def run_agent_job(job_type: str, data: dict):
    orchestrator = AgentOrchestrator()
    result = orchestrator.run(job_type, data)
    return result
