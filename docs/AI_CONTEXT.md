# AI_CONTEXT.md

# AI Workspace - AI Context Memory

## Purpose

This file acts as the persistent memory for the AI coding agent.

Its purpose is to preserve the latest project context so development can continue seamlessly across new chat sessions without losing important information.

This file should always contain the latest state of the project.

---

## Instructions for the AI Coding Agent

You are the dedicated coding agent for this project.

Before performing any task:

1. Read this file completely.
2. Treat this file as the current source of project context.
3. Follow the architecture and design decisions defined in `PROJECT.md`.
4. Never make assumptions that conflict with the documented project direction.
5. Keep implementations modular, production-ready, and consistent with the existing codebase.
6. Do not introduce unnecessary libraries, architectural changes, or unrelated refactoring unless explicitly requested.

---

## Update Rules

After every successful implementation, update this file by modifying only the relevant sections.

Do **not** rewrite the entire file.

Always preserve existing information unless it has become outdated.

---

## Current Project State

### Current Phase

Phase 2 — Authentication (Complete)

### Current Module

Authentication

### Current Objective

Phase 2 authentication is complete. The next planned phase is document management.

---

## Tech Stack

Frontend:
React + TypeScript + Vite

Backend:
FastAPI

AI:
LangChain + LangGraph

Database:
PostgreSQL

Vector Database:
Qdrant

Storage:
MinIO

Cache:
Redis

---

## Important Decisions

* React will be used for the frontend.
* FastAPI will be used for the backend.
* Qdrant will be the primary vector database.
* PostgreSQL will store application data.
* MinIO will store uploaded files.
* The architecture should remain provider-independent.
* All major features should be modular.

---

## Current Architecture Status

Phase 1.5 backend infrastructure hardening is complete.

Phase 2 authentication is complete.

Backend:
- FastAPI initialized with app factory pattern
- Layered architecture: api/core/config/database/models/schemas/services/repositories/middleware/utils
- pydantic-settings for type-safe configuration (grouped by service, Security section added)
- Settings: ENVIRONMENT, SECRET_KEY, JWT_* placeholders ready for Phase 2
- Exception hierarchy: AppException, NotFoundException, ConflictException, UnauthorizedException, ForbiddenException, ValidationException, InternalServerException
- Global exception handlers registered (consistent JSON error envelope)
- Standard response schemas: SuccessResponse[T], ErrorResponse, PaginatedResponse[T], PaginationMeta
- Request ID middleware: stamps every request with UUID, X-Request-ID header
- HTTP logging middleware: method, path, IP, status, execution time
- Dependency injection layer: api/deps.py with get_db, get_app_settings, auth stubs
- Database split: base.py (Base + naming conventions), engine.py (engine + pool), session.py (get_db)
- Alembic configured for async SQLAlchemy; env.py reads DATABASE_URL from settings
- Centralized constants: API_V1_PREFIX, REQUEST_ID_HEADER, pagination defaults, roles
- Utility layer: datetime (UTC-aware), pagination (compute_pagination, get_offset), responses (ok, created, paginated, error)
- Improved health endpoint: status, version, environment, timestamp
- Code quality: pyproject.toml (Ruff + Black + isort); frontend .prettierrc
- Authentication: User and RefreshSession models; Alembic migration; bcrypt password hashing; signed access/refresh JWTs; rotating, revocable refresh sessions; register/login/refresh/logout/me endpoints; HTTP bearer OpenAPI security scheme; reusable current-user/admin dependencies; and an interactive first-admin seeder.
- Security: JWT values are loaded from Settings; production rejects the documented default SECRET_KEY; Swagger is available in development only.

Frontend:
- React + TypeScript + Vite initialized
- Tailwind CSS v4 configured via @tailwindcss/vite plugin
- react-router-dom with AppRoutes registry
- Axios API client pre-configured
- Zustand installed for state management
- Path alias @ mapped to src/
- shadcn/ui structure ready (install components as needed)
- Prettier configured
- Authentication foundation: login page, protected route, Zustand auth store, local token storage, Axios bearer attachment, and one-flight automatic refresh-token rotation.

Infrastructure:
- docker-compose.yml with 6 services: frontend, backend, postgres, redis, minio, qdrant
- Health checks on postgres, redis, minio
- Named volumes for all stateful services

---

## Known Issues

None.

---

## Next Development Goal

Phase 3 — Document Management.

---

## Notes

Keep this file concise.

Only store information that is necessary to continue development in future sessions.

Avoid duplicating information already available in the source code or PROJECT.md.
