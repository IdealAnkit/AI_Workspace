"""
API v1 router.

Aggregates all versioned route modules.
Add new feature routers here as they are implemented in later phases.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
