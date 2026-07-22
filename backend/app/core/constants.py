"""
Application-wide constants.

Keep infrastructure constants here.
Business constants belong in their respective feature modules.
"""

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

API_V1_PREFIX: str = "/api/v1"
API_VERSION: str = "v1"

# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

REQUEST_ID_HEADER: str = "X-Request-ID"
AUTHORIZATION_HEADER: str = "Authorization"
BEARER_PREFIX: str = "Bearer"

# ---------------------------------------------------------------------------
# Pagination defaults
# ---------------------------------------------------------------------------

DEFAULT_PAGE: int = 1
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------

ENV_DEVELOPMENT: str = "development"
ENV_PRODUCTION: str = "production"
ENV_TESTING: str = "testing"

# ---------------------------------------------------------------------------
# Status strings
# ---------------------------------------------------------------------------

STATUS_OK: str = "ok"
STATUS_DEGRADED: str = "degraded"
STATUS_DOWN: str = "down"

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLE_USER: str = "user"
ROLE_ADMIN: str = "admin"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

ACCESS_TOKEN_TYPE: str = "access"
REFRESH_TOKEN_TYPE: str = "refresh"
