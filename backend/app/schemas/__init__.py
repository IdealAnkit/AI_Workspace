"""
Schemas package.

Re-exports all public schema types for convenient importing:
    from app.schemas import SuccessResponse, PaginatedResponse, ErrorResponse
"""

from app.schemas.responses import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from app.schemas.auth import AuthResponse, TokenPairResponse, UserResponse

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "SuccessResponse",
    "AuthResponse",
    "TokenPairResponse",
    "UserResponse",
]
