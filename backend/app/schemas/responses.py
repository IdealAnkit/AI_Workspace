"""
Standard API response schemas.

All API endpoints should return one of these envelopes to guarantee
a consistent response structure across the entire application.

Usage:
    from app.schemas.responses import SuccessResponse, PaginatedResponse

    @router.get("/items", response_model=SuccessResponse[list[ItemSchema]])
    async def list_items() -> SuccessResponse[list[ItemSchema]]:
        ...
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Structured error information nested inside ErrorResponse."""

    code: str = Field(..., description="Machine-readable error code.")
    details: Optional[Any] = Field(
        default=None,
        description="Additional error context (validation errors, etc.).",
    )


class PaginationMeta(BaseModel):
    """Pagination metadata included in paginated responses."""

    page: int = Field(..., ge=1, description="Current page number (1-indexed).")
    size: int = Field(..., ge=1, description="Number of items per page.")
    total: int = Field(..., ge=0, description="Total number of items.")
    pages: int = Field(..., ge=0, description="Total number of pages.")


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response envelope.

    Example:
        {
            "success": true,
            "message": "OK",
            "data": { ... }
        }
    """

    success: bool = True
    message: str = "OK"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """
    Standard error response envelope.

    Example:
        {
            "success": false,
            "message": "The requested resource was not found.",
            "error": { "code": "NOT_FOUND", "details": null }
        }
    """

    success: bool = False
    message: str
    error: ErrorDetail


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response envelope.

    Example:
        {
            "success": true,
            "message": "OK",
            "data": [ ... ],
            "pagination": { "page": 1, "size": 20, "total": 100, "pages": 5 }
        }
    """

    success: bool = True
    message: str = "OK"
    data: list[T] = Field(default_factory=list)
    pagination: PaginationMeta
