"""
Request ID middleware.

Assigns a UUID to every incoming request and echoes it back in the
X-Request-ID response header. Stored on request.state so it can be
read by logger middleware and exception handlers.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique request ID into every request/response cycle."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Honour a pre-existing request ID if the caller sends one (e.g. from
        # an upstream proxy or API gateway); otherwise generate a fresh UUID.
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
