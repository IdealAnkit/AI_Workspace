"""
Global exception handlers.

Registers FastAPI exception handlers that convert all exceptions —
including AppException subclasses and FastAPI's built-in errors —
into a consistent JSON response envelope.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def _error_response(
    status_code: int,
    message: str,
    error_code: str,
    details: object = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Build the standard error JSON envelope."""
    content: dict = {
        "success": False,
        "message": message,
        "error": {
            "code": error_code,
            "details": details,
        },
    }
    if request_id:
        content["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=content)


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            "AppException [%s] %s — %s",
            exc.error_code,
            request.url.path,
            exc.message,
        )
        return _error_response(
            status_code=exc.status_code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            request_id=_get_request_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Request validation failed.",
            error_code="VALIDATION_ERROR",
            details=exc.errors(),
            request_id=_get_request_id(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        error_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            429: "TOO_MANY_REQUESTS",
        }
        error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
        return _error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            error_code=error_code,
            request_id=_get_request_id(request),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception on %s", request.url.path)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An internal server error occurred.",
            error_code="INTERNAL_SERVER_ERROR",
            request_id=_get_request_id(request),
        )
