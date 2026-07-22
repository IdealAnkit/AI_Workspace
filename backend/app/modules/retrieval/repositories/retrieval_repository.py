"""Database-only owner-scoped chunk lookup and retrieval observability persistence."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models.document import Document
from app.modules.indexing.models import DocumentChunk
from app.modules.retrieval.models import QueryHistory, RetrievalLog, RetrievalSession, SearchAnalytics
from app.modules.retrieval.retrievers.types import Query, RetrievedChunk


class RetrievalRepository:
    def __init__(self, session: AsyncSession) -> None: self.session = session

    def _scoped_chunks(self, query: Query):
        conditions = [Document.owner_id == query.user_id, Document.is_deleted.is_(False)]
        if query.workspace_id is not None: conditions.append(Document.workspace_id == query.workspace_id)
        if query.document_ids: conditions.append(DocumentChunk.document_id.in_(query.document_ids))
        if query.language: conditions.append(DocumentChunk.language == query.language)
        return select(DocumentChunk, Document.owner_id, Document.workspace_id, Document.filename).join(Document, DocumentChunk.document_id == Document.id).where(*conditions)

    async def chunks_by_ids(self, ids: list[UUID], query: Query) -> list[RetrievedChunk]:
        if not ids: return []
        result = await self.session.execute(self._scoped_chunks(query).where(DocumentChunk.id.in_(ids)))
        return [self._row_to_chunk(row, 0.0, "semantic") for row in result.all()]

    async def keyword_chunks(self, query: Query, limit: int) -> list[RetrievedChunk]:
        terms = [term for term in query.query.split() if term]
        statement = self._scoped_chunks(query)
        for term in terms:
            statement = statement.where(DocumentChunk.text.ilike(f"%{term}%"))
        result = await self.session.execute(statement.order_by(DocumentChunk.chunk_index.asc()).limit(limit))
        rows = result.all()
        return [self._row_to_chunk(row, self._keyword_score(row[0].text, terms), "keyword") for row in rows]

    @staticmethod
    def _keyword_score(text: str, terms: list[str]) -> float:
        if not terms: return 0.0
        lowered = text.lower()
        return sum(lowered.count(term.lower()) for term in terms) / len(terms)

    @staticmethod
    def _row_to_chunk(row, score: float, source: str) -> RetrievedChunk:
        chunk, owner_id, workspace_id, filename = row
        metadata = dict(chunk.metadata_ or {})
        metadata.setdefault("document_title", filename)
        return RetrievedChunk(id=chunk.id, document_id=chunk.document_id, chunk_index=chunk.chunk_index, text=chunk.text, score=score, source=source, page_start=chunk.page_start, page_end=chunk.page_end, section_title=chunk.section_title, metadata=metadata, language=chunk.language, workspace_id=workspace_id, owner_id=owner_id, checksum=chunk.checksum)

    async def create_session(self, query: Query) -> RetrievalSession:
        item = RetrievalSession(user_id=query.user_id, workspace_id=query.workspace_id, query=query.query, top_k=query.top_k, filters=query.filters)
        self.session.add(item); await self.session.flush(); await self.session.refresh(item); return item

    async def record_search(self, session: RetrievalSession, query: Query, retriever: str, returned: int, duration: float, normalized_query: str) -> QueryHistory:
        history = QueryHistory(retrieval_session_id=session.id, user_id=query.user_id, workspace_id=query.workspace_id, query=query.query, normalized_query=normalized_query, retriever=retriever, top_k=query.top_k, returned_chunks=returned, duration_seconds=duration, filters=query.filters)
        self.session.add(history)
        self.session.add(SearchAnalytics(user_id=query.user_id, workspace_id=query.workspace_id, query=query.query, retriever=retriever, top_k=query.top_k, returned_chunks=returned, duration_seconds=duration, filters=query.filters))
        self.session.add(RetrievalLog(retrieval_session_id=session.id, level="INFO", message=f"Returned {returned} retrieval chunks."))
        await self.session.flush(); await self.session.refresh(history); return history

    async def add_log(self, session_id: UUID, level: str, message: str) -> None:
        self.session.add(RetrievalLog(retrieval_session_id=session_id, level=level, message=message))
        await self.session.flush()

    async def list_history(self, user_id: UUID, offset: int, limit: int) -> tuple[list[QueryHistory], int]:
        base = select(QueryHistory).where(QueryHistory.user_id == user_id)
        result = await self.session.execute(base.order_by(QueryHistory.created_at.desc()).offset(offset).limit(limit))
        total = await self.session.execute(select(func.count()).select_from(QueryHistory).where(QueryHistory.user_id == user_id))
        return list(result.scalars().all()), int(total.scalar_one())

    async def get_history(self, history_id: UUID, user_id: UUID) -> QueryHistory | None:
        result = await self.session.execute(select(QueryHistory).where(QueryHistory.id == history_id, QueryHistory.user_id == user_id))
        return result.scalar_one_or_none()

    async def analytics(self, user_id: UUID) -> tuple[int, float, int]:
        result = await self.session.execute(select(func.count(), func.coalesce(func.avg(SearchAnalytics.duration_seconds), 0), func.coalesce(func.sum(SearchAnalytics.returned_chunks), 0)).where(SearchAnalytics.user_id == user_id))
        count, avg, chunks = result.one()
        return int(count), float(avg), int(chunks)
