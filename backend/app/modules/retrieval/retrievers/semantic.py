from app.modules.indexing.embedders import BaseEmbeddingProvider
from app.modules.indexing.vectordb import BaseVectorStore
from app.modules.retrieval.repositories import RetrievalRepository
from app.modules.retrieval.retrievers.base import BaseRetriever
from app.modules.retrieval.retrievers.types import Query, RetrievedChunk


class SemanticRetriever(BaseRetriever):
    def __init__(self, vector_store: BaseVectorStore, embedding_provider: BaseEmbeddingProvider, repository: RetrievalRepository, collection: str) -> None:
        self.vector_store, self.embedding_provider, self.repository, self.collection = vector_store, embedding_provider, repository, collection
    def supports(self, query: Query) -> bool: return bool(query.query)
    def name(self) -> str: return "semantic"
    async def retrieve(self, query: Query) -> list[RetrievedChunk]:
        vector = await self.embedding_provider.embed(query.query)
        matches = await self.vector_store.search(self.collection, vector, limit=query.top_k * 3)
        score_by_id = {str(match["id"]): float(match.get("score", 0.0)) for match in matches}
        chunks = await self.repository.chunks_by_ids([__import__("uuid").UUID(value) for value in score_by_id], query)
        for chunk in chunks: chunk.score = score_by_id[str(chunk.id)]
        return chunks
