#backend/app/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import api_router

class JDMatcherApp:
    def __init__(self):
        self.app = FastAPI(
            title="Resume-JD Matcher API",
            description="Backend for matching candidate resumes to job descriptions using AI agents.",
            version="0.2.0"
        )
        self._configure_cors()
        self.include_routers()        

    def _configure_cors(self):
        origins_env = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
        origins = [o.strip() for o in origins_env.split(",") if o.strip()]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def include_routers(self):
        self.app.include_router(api_router)

def get_app():
    """Entrypoint for ASGI"""
    return JDMatcherApp().app

# Run with 'uvicorn backend.app.main:get_app'
app = get_app()
