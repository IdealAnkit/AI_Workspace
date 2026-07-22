"""
Centralized exception hierarchy for AI Workspace.

All application errors inherit from AppException, giving every
raised error a consistent structure that maps cleanly to an
HTTP response via the registered exception handlers.
"""

from typing import Any, Optional


class AppException(Exception):
    """
    Base application exception.

    All custom exceptions should inherit from this class.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_SERVER_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)


class ValidationException(AppException):
    """Raised when request data fails validation (422)."""

    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed."


class NotFoundException(AppException):
    """Raised when a requested resource does not exist (404)."""

    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictException(AppException):
    """Raised when an action conflicts with the current state (409)."""

    status_code = 409
    error_code = "CONFLICT"
    message = "A conflict occurred with the current state of the resource."


class UnauthorizedException(AppException):
    """Raised when the request lacks valid authentication (401)."""

    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Authentication is required to access this resource."


class ForbiddenException(AppException):
    """Raised when the authenticated user lacks permission (403)."""

    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class InternalServerException(AppException):
    """Raised for unexpected server-side errors (500)."""

    status_code = 500
    error_code = "INTERNAL_SERVER_ERROR"
    message = "An internal server error occurred."
