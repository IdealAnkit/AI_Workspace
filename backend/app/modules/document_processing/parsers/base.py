"""Abstract parser contract independent from storage and orchestration."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.documents.models.document import Document
from app.modules.document_processing.schemas.parsed import ParsedDocument


class BaseParser(ABC):
    """Extract a supported source format into the shared ParsedDocument model."""

    name: str

    @abstractmethod
    def supports(self, document: Document) -> bool:
        """Return whether this parser can process the document metadata."""

    @abstractmethod
    def extract(self, document_id: UUID, content: bytes, document: Document) -> ParsedDocument:
        """Extract raw text and format-specific metadata."""

    @abstractmethod
    def metadata(self, content: bytes, document: Document) -> dict:
        """Return parser-specific metadata without normalizing it."""
