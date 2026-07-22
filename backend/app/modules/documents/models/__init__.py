"""Document ORM models."""

from app.modules.documents.models.document import (
    ALLOWED_DOCUMENT_STATUS_TRANSITIONS,
    Document,
    DocumentStatus,
)

__all__ = ["ALLOWED_DOCUMENT_STATUS_TRANSITIONS", "Document", "DocumentStatus"]
