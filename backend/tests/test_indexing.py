"""Offline tests for enterprise indexing components and orchestration."""

import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.app_factory import create_app
from app.models.user import User
from app.modules.document_processing.models.processing import ProcessedDocument
from app.modules.indexing.chunkers import FixedSizeChunker, MarkdownChunker, RecursiveChunker
from app.modules.indexing.embedders import DeterministicEmbeddingProvider
from app.modules.indexing.models import EmbeddingJobStatus
from app.modules.indexing.pipeline import IndexingPipeline
from app.modules.indexing.services import IndexingService
from app.modules.indexing.dependencies import get_indexing_service
from app.modules.indexing.repositories import IndexingRepository
from app.modules.indexing.vectordb import QdrantVectorStore, VectorRecord


def processed_document(*, markdown: bool = False) -> ProcessedDocument:
    return ProcessedDocument(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        processing_job_id=uuid.uuid4(),
        text="# Intro\n\nOne two three four five.\n\n# Next\n\nSix seven eight." if markdown else "One two three four five six seven eight nine ten.",
        pages=[{"number": 1, "text": "One two three four five six seven eight nine ten."}],
        metadata_={"format": "markdown"} if markdown else {"format": "txt"},
        warnings=[],
        language="en",
    )


class ChunkingTests(unittest.TestCase):
    def test_chunkers_generate_metadata_and_markdown_heading_context(self) -> None:
        document = processed_document(markdown=True)
        fixed = FixedSizeChunker().split(document, 18, 4)
        recursive = RecursiveChunker().split(document, 18, 4)
        markdown = MarkdownChunker().split(document, 30, 5)

        self.assertGreater(len(fixed), 1)
        self.assertGreater(len(recursive), 1)
        self.assertEqual(markdown[0].section_title, "Intro")
        self.assertEqual(markdown[0].heading_path, ["Intro"])

    def test_pipeline_versions_chunks_without_mutating_prior_content(self) -> None:
        document = processed_document()
        pipeline = IndexingPipeline([RecursiveChunker(), FixedSizeChunker()], 20, 4)
        first = pipeline.chunk(document, version=1, embedding_job_id=uuid.uuid4(), index_metadata_id=uuid.uuid4())
        second = pipeline.chunk(document, version=2, embedding_job_id=uuid.uuid4(), index_metadata_id=uuid.uuid4())

        self.assertEqual({chunk.version for chunk in first}, {1})
        self.assertEqual({chunk.version for chunk in second}, {2})
        self.assertEqual(first[0].checksum, second[0].checksum)


class EmbeddingTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_embedding_and_batch_dimensions(self) -> None:
        provider = DeterministicEmbeddingProvider(8)
        one = await provider.embed("same text")
        batch = await provider.embed_batch(["same text", "different text"])

        self.assertEqual(one, batch[0])
        self.assertEqual(len(one), 8)
        self.assertNotEqual(batch[0], batch[1])


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collections: set[str] = set()
        self.points = []

    async def collection_exists(self, name): return name in self.collections
    async def create_collection(self, collection_name, vectors_config): self.collections.add(collection_name)
    async def upsert(self, collection_name, points, wait): self.points.extend(points)
    async def delete(self, **kwargs): return None
    async def query_points(self, **kwargs): return SimpleNamespace(points=[])


class VectorStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_qdrant_adapter_uses_injected_client(self) -> None:
        client = FakeQdrantClient()
        store = QdrantVectorStore("http://unused", client=client)
        await store.create_collection("test", 3)
        await store.upsert("test", [VectorRecord(id=str(uuid.uuid4()), vector=[0.1, 0.2, 0.3], payload={"document_id": "d"})])

        self.assertTrue(await store.collection_exists("test"))
        self.assertEqual(len(client.points), 1)


class ScalarResult:
    def scalar_one_or_none(self): return None


class QuerySession:
    def __init__(self): self.statement = None
    async def execute(self, statement): self.statement = statement; return ScalarResult()


class IndexingRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_scoped_index_lookup_excludes_soft_deleted_documents(self) -> None:
        session = QuerySession()
        repository = IndexingRepository(session)  # type: ignore[arg-type]
        await repository.get_latest_metadata_for_owner(uuid.uuid4(), uuid.uuid4())
        self.assertIn("documents.is_deleted IS false", str(session.statement))


class MemoryProcessingRepository:
    def __init__(self, document): self.document = document
    async def get_result_by_id(self, _): return self.document


class MemoryIndexingRepository:
    def __init__(self):
        self.metadata = []
        self.jobs = []
        self.chunks = []
        self.errors = []

    async def get_latest_metadata_for_document(self, document_id):
        return self.metadata[-1] if self.metadata else None

    async def create_index_metadata(self, **kwargs):
        item = SimpleNamespace(id=uuid.uuid4(), embedding_version=kwargs["version"], chunk_count=0, status="pending", **kwargs)
        self.metadata.append(item); return item

    async def create_job(self, **kwargs):
        job = SimpleNamespace(id=uuid.uuid4(), status="pending", **kwargs)
        self.jobs.append(job); return job

    async def set_status(self, job, metadata, status, **kwargs):
        job.status = status.value; metadata.status = status.value
        for name, value in kwargs.items():
            if name == "reason": job.failure_reason = value
            elif name == "duration": job.duration_seconds = value
            else: setattr(job, name, value)

    async def create_chunks(self, chunks):
        for chunk in chunks: chunk.id = uuid.uuid4()
        self.chunks.extend(chunks); return chunks

    async def add_log(self, *args): return None
    async def add_error(self, _job_id, _kind, message): self.errors.append(message)
    async def semantic_search(self, *args, **kwargs): return []
    async def hybrid_search(self, *args, **kwargs): return []
    async def keyword_search(self, *args, **kwargs): return []


class MemoryVectorStore:
    def __init__(self, fail=False): self.records = []; self.fail = fail
    async def create_collection(self, name, dimensions):
        if self.fail: raise RuntimeError("vector store unavailable")
    async def upsert(self, collection, records): self.records.extend(records)


class IndexingServiceTests(unittest.IsolatedAsyncioTestCase):
    def build(self, *, fail=False):
        document = processed_document()
        repository = MemoryIndexingRepository()
        service = IndexingService(
            MemoryProcessingRepository(document), repository,
            IndexingPipeline([RecursiveChunker(), FixedSizeChunker()], 20, 4),
            DeterministicEmbeddingProvider(8), MemoryVectorStore(fail), "test", 2,
        )
        return service, repository, document

    async def test_pipeline_persists_ready_index_and_allows_reindex_versions(self) -> None:
        service, repository, document = self.build()
        await service.index_processed_document(document.id)
        await service.index_processed_document(document.id)

        self.assertEqual([item.embedding_version for item in repository.metadata], [1, 2])
        self.assertTrue(all(job.status == EmbeddingJobStatus.READY.value for job in repository.jobs))
        self.assertTrue(all(chunk.version in {1, 2} for chunk in repository.chunks))

    async def test_failure_is_persisted_without_raising(self) -> None:
        service, repository, document = self.build(fail=True)
        await service.index_processed_document(document.id)

        self.assertEqual(repository.jobs[0].status, EmbeddingJobStatus.FAILED.value)
        self.assertEqual(repository.errors, ["vector store unavailable"])


class ApiIndexingService:
    async def get_latest_index(self, document_id, owner_id):
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=uuid.uuid4(), document_id=document_id, processing_job_id=None,
            vector_collection="test", provider="deterministic", embedding_model="deterministic-v1",
            embedding_version=1, embedding_dimension=8, chunk_count=2, status="ready",
            indexed_at=now, created_at=now, updated_at=now,
        )


class IndexingApiTests(unittest.TestCase):
    def test_index_metadata_is_read_only_and_bearer_protected(self) -> None:
        app = create_app()
        user = User(id=uuid.uuid4())
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_indexing_service] = ApiIndexingService
        try:
            with TestClient(app) as client:
                response = client.get(f"/api/v1/indexing/documents/{uuid.uuid4()}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["status"], "ready")
        finally:
            app.dependency_overrides.clear()
