"""Retrieval-only application service; no language model invocation exists here."""

from uuid import UUID

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.retrieval.pipeline import RetrievalPipeline, RetrievalResult
from app.modules.retrieval.repositories import RetrievalRepository
from app.modules.retrieval.retrievers.types import Query


class RetrievalService:
    def __init__(self, repository: RetrievalRepository, pipeline: RetrievalPipeline, default_top_k: int, max_top_k: int, default_score_threshold: float) -> None:
        self.repository, self.pipeline = repository, pipeline
        self.default_top_k, self.max_top_k, self.default_score_threshold = default_top_k, max_top_k, default_score_threshold
    async def search(self, query: Query) -> RetrievalResult:
        if query.top_k > self.max_top_k: raise ValidationException(message=f"top_k cannot exceed {self.max_top_k}.")
        session = await self.repository.create_session(query)
        try:
            result = await self.pipeline.run(query)
        except Exception as exc:
            await self.repository.add_log(session.id, "ERROR", str(exc) or exc.__class__.__name__)
            raise
        await self.repository.record_search(session, query, result.retriever, len(result.chunks), result.duration_seconds, result.normalized_query)
        return result
    async def history(self, user_id: UUID, offset: int, limit: int): return await self.repository.list_history(user_id, offset, limit)
    async def get_history(self, history_id: UUID, user_id: UUID):
        result = await self.repository.get_history(history_id, user_id)
        if result is None: raise NotFoundException(message="Retrieval history not found.")
        return result
    async def analytics(self, user_id: UUID) -> tuple[int, float, int]: return await self.repository.analytics(user_id)
