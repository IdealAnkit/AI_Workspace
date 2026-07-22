"""
HTTP request/response logging middleware.

Logs every inbound request and its response once complete.

Captured fields:
    - Request ID
    - HTTP method
    - URL path + query string
    - Client IP
    - Response status code
    - Execution time (milliseconds)

Sensitive information (Authorization headers, passwords) is never logged.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs HTTP access details for every request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id: str = getattr(request.state, "request_id", "-")
        client_ip: str = self._get_client_ip(request)
        start = time.perf_counter()

        logger.info(
            "→ %s %s | ip=%s | req_id=%s",
            request.method,
            request.url.path,
            client_ip,
            request_id,
        )

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "✗ %s %s | ip=%s | req_id=%s | %.1fms | UNHANDLED EXCEPTION",
                request.method,
                request.url.path,
                client_ip,
                request_id,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "← %s %s | ip=%s | req_id=%s | status=%d | %.1fms",
            request.method,
            request.url.path,
            client_ip,
            request_id,
            response.status_code,
            elapsed_ms,
        )
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP, checking forwarded headers first."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
