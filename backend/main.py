"""
AI Workspace - FastAPI Backend

Entry point for the backend application.
Run with: uvicorn main:app --reload
"""

from app.core.app_factory import create_app

app = create_app()
