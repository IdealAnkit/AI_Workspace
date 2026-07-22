"""Internal provider-neutral retrieval values."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Query:
    query: str
    workspace_id: UUID | None
    user_id: UUID
    document_ids: list[UUID] = field(default_factory=list)
    language: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    top_k: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime | None = None
    future_options: dict[str, Any] = field(default_factory=dict)
    score_threshold: float = 0.0


@dataclass
class RetrievedChunk:
    id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    score: float
    source: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    metadata: dict[str, Any]
    language: str | None = None
    workspace_id: UUID | None = None
    owner_id: UUID | None = None
    checksum: str | None = None
    ranking_metadata: dict[str, Any] = field(default_factory=dict)
