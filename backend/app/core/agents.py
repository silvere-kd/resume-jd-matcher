# backend/app/core/agents.py

from dataclasses import dataclass
from typing import Any
from crewai import Agent, LLM

@dataclass
class MatcherAgents:
    resume_parser: Agent
    jd_parser: Agent
    matcher: Agent
    enhancer: Agent
    cover_letter: Agent

class AgentsFactory:
    """Factory that builds all CrewAI agents with a shared LLM."""
    def __init__(self, llm: LLM):
        self.llm = llm

    def build(self) -> MatcherAgents:
        resume_parser = Agent(
            role="Resume Parsing Specialist",
            goal="Extract structured data (skills, experience, education, tools) from a resume.",
            backstory="You are meticulous and consistent. Output JSON only.",
            llm=self.llm,
            verbose=False
        )
        jd_parser = Agent(
            role="Job Description Analyst",
            goal="Extract required skills, responsibilities, and must-haves from a JD.",
            backstory="You identify core requirements and hiring signals. Output JSON only.",
            llm=self.llm,
            verbose=False
        )
        matcher = Agent(
            role="Resume-JD Matcher",
            goal="Compare parsed resume vs parsed JD. Score 0-100 and list strengths and gaps.",
            backstory="You are objective and concise. Output JSON only.",
            llm=self.llm,
            verbose=False
        )
        enhancer = Agent(
            role="Resume Enhancer",
            goal="Suggest resume improvements aligned with the JD and rewrite 3–5 key bullets.",
            backstory="Keep it ATS-friendly and specific. Output Markdown.",
            llm=self.llm,
            verbose=False
        )
        cover_letter = Agent(
            role="Cover Letter Writer",
            goal="Draft a tailored one-page cover letter aligned with resume and JD.",
            backstory="Professional, concise, concrete achievements. Output Markdown.",
            llm=self.llm,
            verbose=False
        )

        return MatcherAgents(
            resume_parser=resume_parser,
            jd_parser=jd_parser,
            matcher=matcher,
            enhancer=enhancer,
            cover_letter=cover_letter
        )
