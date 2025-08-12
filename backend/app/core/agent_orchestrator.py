
# backend/app/core/agent_orchestrator.py
from typing import Dict, Any
from crewai import Task, Crew, LLM, Process
from backend.app.config import settings
from backend.app.core.agents import AgentsFactory
import json

class AgentOrchestrator:
    """Handles agent pipeline for resume-JD matching."""
    def __init__(self):
        # We will build LLM here
        model_id = settings.full_model_id()
        self.llm = LLM(
            model=model_id,
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )

    def _common_validate(self, data: Dict[str, Any]):
        resume = (data or {}).get("resume") or ""
        jd = (data or {}).get("jd") or ""
        if not resume.strip() or not jd.strip():
            raise ValueError("Both 'resume' and 'jd' text are required.")
        return resume, jd
    
    def _build_parsing_tasks(self, agents, resume: str, jd: str):
        resume_task = Task(
            description=f"Extract structured JSON from the resume text below.\nReturn keys: skills, experience, education, tools.\n\nRESUME:\n{resume}",
            expected_output="Valid JSON with keys: skills, experience, education, tools.",
            agent=agents.resume_parser
        )
        jd_task = Task(
            description=f"Extract structured JSON from the job description below.\nReturn keys: must_haves, nice_to_haves, responsibilities, keywords.\n\nJD:\n{jd}",
            expected_output="Valid JSON with keys: must_haves, nice_to_haves, responsibilities, keywords.",
            agent=agents.jd_parser
        )
        return resume_task, jd_task

    def run(self, job_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        job_type = (job_type or "").lower()
        if job_type not in {"match", "enhance", "cover_letter"}:
            raise ValueError(f"Unsupported job_type: {job_type}")

        resume, jd = self._common_validate(data)
        agents = AgentsFactory(self.llm).build()

        if job_type == "match":
            resume_task, jd_task = self._build_parsing_tasks(agents, resume, jd)
            match_task = Task(
                description=(
                    "Compare the parsed resume vs parsed JD and return a JSON with keys: "
                    "match_score (0-100 integer), strengths (list), gaps (list), summary (string)."
                ),
                expected_output="Valid JSON with keys: match_score, strengths, gaps, summary.",
                agent=agents.matcher,
                context=[resume_task, jd_task]
            )
            crew = Crew(
                agents=[agents.resume_parser, agents.jd_parser, agents.matcher],
                tasks=[resume_task, jd_task, match_task],
                process=Process.sequential,
                verbose=False,
                name="MatchCrew",
                description="Parses resume and JD, then computes a structured match report."
            )
            result = crew.kickoff()
            raw = getattr(result, "raw", None)
            if not raw:
                return {"status": "done", "result": {"raw": str(result)}}
            try:
                return {"status": "done", "result": json.loads(raw)}
            except Exception:
                return {"status": "done", "result": {"raw": raw}}

        if job_type == "enhance":
            resume_task, jd_task = self._build_parsing_tasks(agents, resume, jd)
            enhance_task = Task(
                description=(
                    "Using parsed resume and JD, suggest concrete improvements and rewrite 3–5 bullets. "
                    "Return Markdown with sections: 'Improvements' and 'Rewritten Bullets'."
                ),
                expected_output="Markdown with 'Improvements' and 'Rewritten Bullets' sections.",
                agent=agents.enhancer,
                context=[resume_task, jd_task]
            )
            crew = Crew(
                agents=[agents.resume_parser, agents.jd_parser, agents.enhancer],
                tasks=[resume_task, jd_task, enhance_task],
                process=Process.sequential,
                verbose=False,
                name="EnhanceCrew",
                description="Parses resume and JD, then produces targeted enhancements."
            )
            result = crew.kickoff()
            return {"status": "done", "result": {"resume_enhancement_md": getattr(result, "raw", str(result))}}

        if job_type == "cover_letter":
            resume_task, jd_task = self._build_parsing_tasks(agents, resume, jd)
            cl_task = Task(
                description="Draft a tailored one-page cover letter in Markdown based on parsed resume and JD.",
                expected_output="A Markdown-formatted cover letter.",
                agent=agents.cover_letter,
                context=[resume_task, jd_task]
            )
            crew = Crew(
                agents=[agents.resume_parser, agents.jd_parser, agents.cover_letter],
                tasks=[resume_task, jd_task, cl_task],
                process=Process.sequential,
                verbose=False,
                name="CoverLetterCrew",
                description="Parses resume and JD, then writes a tailored cover letter."
            )
            result = crew.kickoff()
            return {"status": "done", "result": {"cover_letter_md": getattr(result, "raw", str(result))}}

        raise RuntimeError("Unreachable.")
