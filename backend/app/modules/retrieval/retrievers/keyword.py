from app.modules.retrieval.repositories import RetrievalRepository
from app.modules.retrieval.retrievers.base import BaseRetriever
from app.modules.retrieval.retrievers.types import Query, RetrievedChunk


class KeywordRetriever(BaseRetriever):
    def __init__(self, repository: RetrievalRepository) -> None: self.repository = repository
    def supports(self, query: Query) -> bool: return bool(query.query)
    def name(self) -> str: return "keyword"
    async def retrieve(self, query: Query) -> list[RetrievedChunk]: return await self.repository.keyword_chunks(query, query.top_k * 3)
