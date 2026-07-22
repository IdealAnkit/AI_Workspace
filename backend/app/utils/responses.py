"""
Response factory helpers.

Convenience functions for constructing standard response envelopes
without repeating boilerplate in every endpoint.

Usage:
    from app.utils.responses import ok, paginated

    return ok(data=items, message="Documents fetched.")
    return paginated(data=items, pagination=meta)
"""

from typing import Any, Optional, TypeVar

from app.schemas.responses import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)

T = TypeVar("T")


def ok(
    data: Any = None,
    message: str = "OK",
) -> SuccessResponse:
    """Build a standard success response."""
    return SuccessResponse(success=True, message=message, data=data)


def created(
    data: Any = None,
    message: str = "Created successfully.",
) -> SuccessResponse:
    """Build a 201-style success response (data wrapper only; status code set by router)."""
    return SuccessResponse(success=True, message=message, data=data)


def paginated(
    data: list,
    pagination: PaginationMeta,
    message: str = "OK",
) -> PaginatedResponse:
    """Build a paginated success response."""
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        pagination=pagination,
    )


def error(
    message: str,
    code: str = "ERROR",
    details: Optional[Any] = None,
) -> ErrorResponse:
    """Build a standard error response (for use outside exception handlers)."""
    return ErrorResponse(
        success=False,
        message=message,
        error=ErrorDetail(code=code, details=details),
    )
