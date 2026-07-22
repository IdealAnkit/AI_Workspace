"""Synchronous orchestration of immutable chunking, embeddings, and vector publication."""

import time
from uuid import UUID

from app.core.logging import get_logger
from app.core.exceptions import NotFoundException
from app.modules.document_processing.repositories.processing_repository import ProcessingRepository
from app.modules.indexing.embedders import BaseEmbeddingProvider
from app.modules.indexing.models import EmbeddingJobStatus
from app.modules.indexing.pipeline import IndexingPipeline
from app.modules.indexing.repositories import IndexingRepository
from app.modules.indexing.vectordb import BaseVectorStore, VectorRecord
from app.utils.datetime import utcnow

logger = get_logger(__name__)


class IndexingService:
    """Business workflow that is independent of chunker, embedder, and vector implementation."""

    def __init__(self, processing_repository: ProcessingRepository, indexing_repository: IndexingRepository, pipeline: IndexingPipeline, embedding_provider: BaseEmbeddingProvider, vector_store: BaseVectorStore, collection: str, batch_size: int) -> None:
        self.processing_repository = processing_repository
        self.indexing_repository = indexing_repository
        self.pipeline = pipeline
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.collection = collection
        self.batch_size = batch_size

    async def index_processed_document(self, processed_document_id: UUID) -> None:
        """Create a new index version; never alter chunks or vectors from earlier runs."""
        processed = await self.processing_repository.get_result_by_id(processed_document_id)
        if processed is None:
            logger.warning("Skipping indexing for unavailable processed document %s", processed_document_id)
            return
        previous = await self.indexing_repository.get_latest_metadata_for_document(processed.document_id)
        version = (previous.embedding_version + 1) if previous else 1
        metadata = await self.indexing_repository.create_index_metadata(
            document_id=processed.document_id,
            processing_job_id=processed.processing_job_id,
            collection=self.collection,
            provider=self.embedding_provider.provider_name(),
            model=self.embedding_provider.model_name(),
            version=version,
            dimensions=self.embedding_provider.dimensions(),
        )
        job = await self.indexing_repository.create_job(
            document_id=processed.document_id,
            processing_job_id=processed.processing_job_id,
            index_metadata_id=metadata.id,
            provider=self.embedding_provider.provider_name(),
            model=self.embedding_provider.model_name(),
            dimensions=self.embedding_provider.dimensions(),
        )
        started = utcnow()
        clock = time.perf_counter()
        try:
            await self.indexing_repository.add_log(job.id, "INFO", "Indexing job queued.")
            await self.indexing_repository.set_status(job, metadata, EmbeddingJobStatus.CHUNKING, started_at=started)
            chunks = self.pipeline.chunk(processed, version=version, embedding_job_id=job.id, index_metadata_id=metadata.id)
            await self.indexing_repository.create_chunks(chunks)
            metadata.chunk_count = len(chunks)
            await self.indexing_repository.add_log(job.id, "INFO", f"Created {len(chunks)} immutable chunks.")
            await self.indexing_repository.set_status(job, metadata, EmbeddingJobStatus.EMBEDDING)
            vectors = await self._embed_chunks(chunks)
            await self.indexing_repository.set_status(job, metadata, EmbeddingJobStatus.INDEXING)
            await self.vector_store.create_collection(self.collection, self.embedding_provider.dimensions())
            await self._upsert_vectors(chunks, vectors)
            finished = utcnow()
            await self.indexing_repository.set_status(job, metadata, EmbeddingJobStatus.READY, finished_at=finished, duration=time.perf_counter() - clock)
            await self.indexing_repository.add_log(job.id, "INFO", "Index version published successfully.")
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            logger.exception("Indexing failed for processed document %s", processed_document_id)
            await self.indexing_repository.set_status(job, metadata, EmbeddingJobStatus.FAILED, finished_at=utcnow(), duration=time.perf_counter() - clock, reason=message)
            await self.indexing_repository.add_error(job.id, exc.__class__.__name__, message)
            await self.indexing_repository.add_log(job.id, "ERROR", "Indexing failed; error persisted.")

    async def _embed_chunks(self, chunks: list) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(chunks), self.batch_size):
            batch = chunks[start : start + self.batch_size]
            vectors.extend(await self.embedding_provider.embed_batch([chunk.text for chunk in batch]))
        if len(vectors) != len(chunks):
            raise ValueError("Embedding provider returned an unexpected vector count.")
        if any(len(vector) != self.embedding_provider.dimensions() for vector in vectors):
            raise ValueError("Embedding provider returned an unexpected vector dimension.")
        return vectors

    async def _upsert_vectors(self, chunks: list, vectors: list[list[float]]) -> None:
        for start in range(0, len(chunks), self.batch_size):
            records = [
                VectorRecord(
                    id=str(chunk.id),
                    vector=vector,
                    payload={
                        "document_id": str(chunk.document_id),
                        "processing_job_id": str(chunk.processing_job_id) if chunk.processing_job_id else None,
                        "index_metadata_id": str(chunk.index_metadata_id),
                        "chunk_index": chunk.chunk_index,
                        "page_start": chunk.page_start,
                        "page_end": chunk.page_end,
                        "section_title": chunk.section_title,
                        "language": chunk.language,
                        "version": chunk.version,
                    },
                )
                for chunk, vector in zip(chunks[start : start + self.batch_size], vectors[start : start + self.batch_size])
            ]
            await self.vector_store.upsert(self.collection, records)

    async def semantic_search(self, *args, **kwargs) -> list:
        return await self.indexing_repository.semantic_search(*args, **kwargs)

    async def hybrid_search(self, *args, **kwargs) -> list:
        return await self.indexing_repository.hybrid_search(*args, **kwargs)

    async def keyword_search(self, *args, **kwargs) -> list:
        return await self.indexing_repository.keyword_search(*args, **kwargs)

    async def get_latest_index(self, document_id: UUID, owner_id: UUID):
        metadata = await self.indexing_repository.get_latest_metadata_for_owner(document_id, owner_id)
        if metadata is None:
            raise NotFoundException(message="Index metadata not found.")
        return metadata
