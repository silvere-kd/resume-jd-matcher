#backend/app/main.py

from fastapi import FastAPI
from backend.app.api.routes import api_router

class JDMatcherApp:
    def __init__(self):
        self.app = FastAPI(
            title="Resume-JD Matcher API",
            description="Backend for matching candidate resumes to job descriptions using AI agents.",
            version="0.1.0"
        )
        self.include_routers()


    def include_routers(self):
        self.app.include_router(api_router)

def get_app():
    """Entrypoint for ASGI"""
    return JDMatcherApp().app

# Run with 'uvicorn backend.app.main:get_app'
app = get_app()
