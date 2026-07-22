"""Common internal structured-document representation returned by every parser."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    """Normalized text from one logical source page."""

    number: int = Field(ge=1)
    text: str = ""


class ParsedDocument(BaseModel):
    """Parser-neutral content that flows through normalization and persistence."""

    document_id: UUID
    title: str | None = None
    language: str | None = None
    page_count: int | None = None
    pages: list[ParsedPage] = Field(default_factory=list)
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    processing_time_seconds: float = 0.0
