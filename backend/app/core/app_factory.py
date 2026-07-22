"""
Application factory.

Creates and fully configures the FastAPI application instance.
- Middleware is registered in the correct order (LIFO execution)
- Exception handlers cover all error types
- API routers are versioned under /api/v1
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware import LoggingMiddleware, RequestIDMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown hooks."""
    configure_logging()
    # Phase 2+: initialise DB connection pool, Redis, MinIO clients here
    yield
    # Phase 2+: close connections gracefully here


def create_app() -> FastAPI:
    """Create, configure, and return the FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        # Interactive API documentation is intentionally unavailable in production.
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Exception handlers
    # ------------------------------------------------------------------
    register_exception_handlers(app)

    # ------------------------------------------------------------------
    # Middleware (registered in reverse execution order — last added runs first)
    #
    # Execution order for an incoming request:
    #   1. RequestIDMiddleware  → stamps request with UUID
    #   2. LoggingMiddleware    → logs request/response
    #   3. CORSMiddleware       → adds CORS headers
    # ------------------------------------------------------------------
    app.add_middleware(CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(api_router, prefix="/api/v1")

    return app
