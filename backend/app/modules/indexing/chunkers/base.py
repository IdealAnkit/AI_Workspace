"""Replaceable document chunking contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.modules.document_processing.models.processing import ProcessedDocument


@dataclass(frozen=True)
class ChunkDraft:
    """Provider-neutral, not-yet-persisted immutable chunk content."""

    text: str
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    heading_path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseChunker(ABC):
    """Split a processed document without knowing embeddings or storage."""

    name: str

    @abstractmethod
    def supports(self, document: ProcessedDocument) -> bool: ...

    @abstractmethod
    def split(self, document: ProcessedDocument, chunk_size: int, overlap: int) -> list[ChunkDraft]: ...

    @abstractmethod
    def metadata(self, document: ProcessedDocument) -> dict[str, Any]: ...
