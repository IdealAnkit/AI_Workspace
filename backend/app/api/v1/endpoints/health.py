"""
Health check endpoint.

Returns application status, version, environment, and current UTC timestamp.
Used by Docker HEALTHCHECK, load balancers, and monitoring systems.

Future phases can extend this to include database/Redis/MinIO liveness checks.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config.settings import get_settings
from app.core.constants import STATUS_OK
from app.utils.datetime import format_iso_now

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    environment: str
    timestamp: str


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description=(
        "Returns the current health status, application version, "
        "environment, and server timestamp. "
        "Does not check external services."
    ),
)
async def health_check() -> HealthResponse:
    """Liveness probe — always returns 200 if the process is running."""
    settings = get_settings()
    return HealthResponse(
        status=STATUS_OK,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=format_iso_now(),
    )
