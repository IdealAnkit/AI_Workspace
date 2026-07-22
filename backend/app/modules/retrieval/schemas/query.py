"""Public query and result contracts for retrieval-only APIs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000, examples=["How is document processing triggered?"])
    workspace_id: UUID | None = None
    document_ids: list[UUID] = Field(default_factory=list)
    language: str | None = Field(default=None, max_length=16)
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int | None = Field(default=None, ge=1)
    score_threshold: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    future_options: dict[str, Any] = Field(default_factory=dict)


class CitationResponse(BaseModel):
    document_id: UUID
    document_title: str | None
    chunk_id: UUID
    chunk_index: int
    page_number: int | None
    section_title: str | None
    score: float
    metadata: dict[str, Any]


class RetrievedChunkResponse(BaseModel):
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
    ranking_metadata: dict[str, Any]
    citation: CitationResponse


class RetrievalResultResponse(BaseModel):
    query: str
    normalized_query: str
    retriever: str
    chunks: list[RetrievedChunkResponse]
    search_statistics: dict[str, Any]
    retrieval_metadata: dict[str, Any]
    duration_seconds: float


class QueryHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    retrieval_session_id: UUID
    query: str
    normalized_query: str
    retriever: str
    top_k: int
    returned_chunks: int
    duration_seconds: float
    filters: dict[str, Any]
    created_at: datetime


class SearchAnalyticsResponse(BaseModel):
    total_searches: int
    average_duration_seconds: float
    total_returned_chunks: int
