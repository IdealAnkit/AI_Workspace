"""In-process event contracts reserved for future document ingestion infrastructure."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DocumentUploadedEvent:
    """Raised after a document's bytes and metadata have been stored."""

    document_id: UUID
    owner_id: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class DocumentDeletedEvent:
    """Raised after a document has been soft-deleted."""

    document_id: UUID
    owner_id: UUID
    deleted_by: UUID
    occurred_at: datetime


class DocumentEventPublisher(ABC):
    """Contract for document lifecycle notifications."""

    @abstractmethod
    async def publish(self, event: DocumentUploadedEvent | DocumentDeletedEvent) -> None:
        """Publish an event without coupling the service to any transport."""


class NoOpDocumentEventPublisher(DocumentEventPublisher):
    """Default publisher; events are invoked locally but not sent externally."""

    async def publish(self, event: DocumentUploadedEvent | DocumentDeletedEvent) -> None:
        return None
