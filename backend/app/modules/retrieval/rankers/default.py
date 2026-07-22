from abc import ABC, abstractmethod

from app.modules.retrieval.retrievers.types import Query, RetrievedChunk


class BaseRanker(ABC):
    @abstractmethod
    def rank(self, chunks: list[RetrievedChunk], query: Query) -> list[RetrievedChunk]: ...
    @abstractmethod
    def supports(self, query: Query) -> bool: ...


class DefaultScoreRanker(BaseRanker):
    def supports(self, query: Query) -> bool: return True
    def rank(self, chunks: list[RetrievedChunk], query: Query) -> list[RetrievedChunk]:
        return sorted((chunk for chunk in chunks if chunk.score >= query.score_threshold), key=lambda chunk: (-chunk.score, chunk.chunk_index))
