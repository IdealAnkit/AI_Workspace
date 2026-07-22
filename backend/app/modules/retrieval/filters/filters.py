"""Composable post-retrieval filters; owner isolation is also enforced in SQL."""

from abc import ABC, abstractmethod
from datetime import datetime

from app.modules.retrieval.retrievers.types import Query, RetrievedChunk


class BaseFilter(ABC):
    @abstractmethod
    def allows(self, chunk: RetrievedChunk, query: Query) -> bool: ...


class OwnerFilter(BaseFilter):
    def allows(self, chunk, query): return chunk.owner_id in {None, query.user_id}


class WorkspaceFilter(BaseFilter):
    def allows(self, chunk, query): return query.workspace_id is None or chunk.workspace_id == query.workspace_id


class DocumentFilter(BaseFilter):
    def allows(self, chunk, query): return not query.document_ids or chunk.document_id in query.document_ids


class MetadataFilter(BaseFilter):
    def allows(self, chunk, query):
        expected = query.filters.get("metadata", {})
        return all(chunk.metadata.get(key) == value for key, value in expected.items())


class LanguageFilter(BaseFilter):
    def allows(self, chunk, query): return query.language is None or chunk.language == query.language


class DateFilter(BaseFilter):
    def allows(self, chunk, query):
        after = query.filters.get("created_after")
        if not after:
            return True
        value = chunk.metadata.get("created_at")
        return value is None or str(value) >= str(after)


class TagFilter(BaseFilter):
    def allows(self, chunk, query):
        requested = set(query.filters.get("tags", []))
        return not requested or requested.intersection(set(chunk.metadata.get("tags", [])))


class FilterPipeline:
    def __init__(self, filters: list[BaseFilter]) -> None: self.filters = filters
    def apply(self, chunks: list[RetrievedChunk], query: Query) -> list[RetrievedChunk]:
        return [chunk for chunk in chunks if all(item.allows(chunk, query) for item in self.filters)]
