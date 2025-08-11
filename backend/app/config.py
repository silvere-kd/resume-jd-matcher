# backend/app/config.py

from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # LLM config
    LLM_PROVIDER: str = Field(default=os.getenv("LLM_PROVIDER", "ollama"))
    LLM_API_KEY: str = Field(default=os.getenv("LLM_API_KEY", "ollama"))
    LLM_BASE_URL: str = Field(default=os.getenv("LLM_BASE_URL", "http://ollama:11434"))
    #LLM_BASE_URL: str = Field(default=os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434"))
    LLM_MODEL_NAME: str = Field(default=os.getenv("LLM_MODEL_NAME", "llama3.2"))
    LLM_TEMPERATURE: str = Field(default=float(os.getenv("LLM_TEMPERATURE", "0.0")))

    # Celery/Redis
    REDIS_URL: str = Field(default=os.getenv("REDIS_URL", "redis://host.docker.internal:6379/0"))

    def full_model_id(self) -> str:
        """
        Return provider-prefixed model id for LiteLLM, e.g.:
        - 'ollama/llama3.2'
        - 'openai/gpt-4o-mini'
        - 'groq/llama3-8b-8192'
        """
        provider = self.LLM_PROVIDER.strip().lower()
        # If already prefixed, keep as is
        if "/" in self.LLM_MODEL_NAME:
            return self.LLM_MODEL_NAME
        return f"{provider}/{self.LLM_MODEL_NAME}"


settings = Settings()
