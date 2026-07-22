"""
API v1 router.

Aggregates all versioned route modules.
Add new feature routers here as they are implemented in later phases.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, health
from app.modules.documents.api.router import router as documents_router
from app.modules.document_processing.api.router import document_processing_router, processing_router
from app.modules.indexing.api.router import router as indexing_router

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(processing_router, prefix="/processing", tags=["Document Processing"])
api_router.include_router(document_processing_router, prefix="/documents", tags=["Document Processing"])
api_router.include_router(indexing_router, prefix="/indexing", tags=["Indexing"])
