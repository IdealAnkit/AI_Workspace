"""Offline tests for modular, owner-scoped retrieval without an LLM."""

import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.app_factory import create_app
from app.models.user import User
from app.modules.indexing.embedders import DeterministicEmbeddingProvider
from app.modules.retrieval.citations import CitationBuilder
from app.modules.retrieval.context import ContextBuilder
from app.modules.retrieval.dependencies import get_retrieval_service
from app.modules.retrieval.filters import DocumentFilter, FilterPipeline, LanguageFilter, OwnerFilter, WorkspaceFilter
from app.modules.retrieval.pipeline import RetrievalPipeline, RetrievalResult
from app.modules.retrieval.rankers import DefaultScoreRanker
from app.modules.retrieval.repositories import RetrievalRepository
from app.modules.retrieval.retrievers import HybridRetriever, KeywordRetriever, SemanticRetriever
from app.modules.retrieval.retrievers.types import Query, RetrievedChunk
from app.modules.retrieval.services import RetrievalService
from app.modules.retrieval.utils import QueryNormalizer


def candidate(*, score=0.5, chunk_index=0, document_id=None, owner_id=None, workspace_id=None, checksum="same", source="semantic"):
    return RetrievedChunk(id=uuid.uuid4(), document_id=document_id or uuid.uuid4(), chunk_index=chunk_index, text=f"Chunk {chunk_index} document content", score=score, source=source, page_start=1, page_end=1, section_title="Overview", metadata={"document_title": "Guide", "tags": ["guide"]}, language="en", owner_id=owner_id, workspace_id=workspace_id, checksum=checksum)


class MemoryRepository:
    def __init__(self, chunks): self.chunks = chunks
    async def chunks_by_ids(self, ids, query): return [chunk for chunk in self.chunks if chunk.id in ids]
    async def keyword_chunks(self, query, limit): return [chunk for chunk in self.chunks if query.query.split()[0] in chunk.text.casefold()][:limit]


class MemoryVectorStore:
    def __init__(self, chunks): self.chunks = chunks
    async def search(self, collection, vector, limit): return [{"id": str(chunk.id), "score": chunk.score} for chunk in self.chunks[:limit]]


class RetrieverTests(unittest.IsolatedAsyncioTestCase):
    async def test_semantic_keyword_and_weighted_hybrid_retrieval(self) -> None:
        owner = uuid.uuid4(); chunks = [candidate(score=0.8, owner_id=owner, checksum="a"), candidate(score=0.4, owner_id=owner, checksum="b", source="keyword")]
        repository = MemoryRepository(chunks)
        query = Query(query="chunk", workspace_id=None, user_id=owner, top_k=2)
        semantic = SemanticRetriever(MemoryVectorStore(chunks), DeterministicEmbeddingProvider(8), repository, "test")
        keyword = KeywordRetriever(repository)
        hybrid = HybridRetriever(semantic, keyword, 0.7, 0.3)

        self.assertEqual(len(await semantic.retrieve(query)), 2)
        self.assertEqual(len(await keyword.retrieve(query)), 2)
        combined = await hybrid.retrieve(query)
        self.assertEqual(len(combined), 2)
        self.assertTrue(all(item.source == "hybrid" for item in combined))

    async def test_filter_ranking_context_and_citation_are_composable(self) -> None:
        owner, workspace, document = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        query = Query(query="chunk", workspace_id=workspace, user_id=owner, document_ids=[document], language="en", top_k=5, score_threshold=0.2)
        first = candidate(score=0.8, chunk_index=0, document_id=document, owner_id=owner, workspace_id=workspace, checksum="duplicate")
        duplicate = candidate(score=0.7, chunk_index=1, document_id=document, owner_id=owner, workspace_id=workspace, checksum="duplicate")
        rejected = candidate(score=0.9, owner_id=uuid.uuid4(), workspace_id=workspace)
        filters = FilterPipeline([OwnerFilter(), WorkspaceFilter(), DocumentFilter(), LanguageFilter()])
        ranked = DefaultScoreRanker().rank(filters.apply([first, duplicate, rejected], query), query)
        context = ContextBuilder(100).build(ranked)

        self.assertEqual(len(context), 1)
        citation = CitationBuilder().build(context[0])
        self.assertEqual(citation["document_id"], document)
        self.assertEqual(citation["chunk_index"], 0)

    def test_query_normalization_removes_unicode_whitespace_and_repeated_punctuation(self) -> None:
        self.assertEqual(QueryNormalizer().normalize("  CAFÉ   PROCESSING!!! "), "café processing!")


class SessionRepository:
    def __init__(self): self.recorded = None
    async def create_session(self, query): return SimpleNamespace(id=uuid.uuid4())
    async def record_search(self, *args): self.recorded = args
    async def list_history(self, user, offset, limit): return [], 0
    async def get_history(self, history, user): return None
    async def analytics(self, user): return 0, 0.0, 0


class FixedPipeline:
    async def run(self, query):
        return RetrievalResult(query=query.query, normalized_query="normalized", retriever="hybrid", chunks=[], citations=[], search_statistics={}, retrieval_metadata={}, duration_seconds=0.01)


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_persists_auditable_history_and_max_top_k_failure(self) -> None:
        repo = SessionRepository(); user = uuid.uuid4()
        service = RetrievalService(repo, FixedPipeline(), 5, 10, 0.0)
        await service.search(Query(query="test", workspace_id=None, user_id=user, top_k=5))
        self.assertEqual(repo.recorded[-1], "normalized")
        with self.assertRaises(Exception):
            await service.search(Query(query="test", workspace_id=None, user_id=user, top_k=11))


class ScalarResult:
    def __init__(self, value=None): self.value = value
    def scalar_one_or_none(self): return self.value
    def all(self): return []


class QuerySession:
    def __init__(self): self.statement = None
    async def execute(self, statement): self.statement = statement; return ScalarResult()


class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunk_queries_include_owner_and_soft_delete_isolation(self) -> None:
        session = QuerySession(); repository = RetrievalRepository(session)  # type: ignore[arg-type]
        await repository.chunks_by_ids([uuid.uuid4()], Query(query="x", workspace_id=None, user_id=uuid.uuid4()))
        sql = str(session.statement)
        self.assertIn("documents.owner_id", sql)
        self.assertIn("documents.is_deleted IS false", sql)


class ApiService:
    default_top_k = 8; default_score_threshold = 0.0
    async def search(self, query):
        item = candidate(owner_id=query.user_id)
        return RetrievalResult(query=query.query, normalized_query=query.query, retriever="hybrid", chunks=[item], citations=[CitationBuilder().build(item)], search_statistics={"returned_chunks": 1}, retrieval_metadata={}, duration_seconds=0.01)
    async def history(self, user, offset, limit): return [], 0
    async def get_history(self, item, user): return SimpleNamespace(id=item, retrieval_session_id=uuid.uuid4(), query="q", normalized_query="q", retriever="hybrid", top_k=1, returned_chunks=1, duration_seconds=0.1, filters={}, created_at=datetime.now(UTC))
    async def analytics(self, user): return 1, 0.1, 1


class ApiTests(unittest.TestCase):
    def test_retrieval_api_returns_chunks_not_answer_text(self) -> None:
        app = create_app(); user = User(id=uuid.uuid4())
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_retrieval_service] = ApiService
        try:
            with TestClient(app) as client:
                response = client.post("/api/v1/retrieval/search", json={"query": "Document processing!!!", "top_k": 3})
                history = client.get("/api/v1/retrieval/history")
                analytics = client.get("/api/v1/retrieval/analytics")
            self.assertEqual(response.status_code, 200)
            self.assertIn("chunks", response.json()["data"])
            self.assertNotIn("answer", response.json()["data"])
            self.assertEqual(history.status_code, 200)
            self.assertEqual(analytics.json()["data"]["total_searches"], 1)
        finally: app.dependency_overrides.clear()
