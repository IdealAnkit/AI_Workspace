"""Dependency injection for independently replaceable indexing components."""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DatabaseDep, SettingsDep
from app.config.settings import Settings
from app.modules.document_processing.events.base import NoOpProcessingEventPublisher, ProcessingEventPublisher, SynchronousProcessingEventPublisher
from app.modules.document_processing.repositories.processing_repository import ProcessingRepository
from app.modules.indexing.chunkers import FixedSizeChunker, MarkdownChunker, RecursiveChunker
from app.modules.indexing.embedders import DeterministicEmbeddingProvider
from app.modules.indexing.events import IndexingEventConsumer
from app.modules.indexing.pipeline import IndexingPipeline
from app.modules.indexing.repositories import IndexingRepository
from app.modules.indexing.services import IndexingService
from app.modules.indexing.vectordb import QdrantVectorStore


def build_indexing_service(db, settings: Settings) -> IndexingService:
    if settings.EMBEDDING_PROVIDER != "deterministic":
        raise ValueError("Only the deterministic embedding provider is available in this phase.")
    if settings.VECTOR_STORE_PROVIDER != "qdrant":
        raise ValueError("Only the Qdrant vector store is available in this phase.")
    pipeline = IndexingPipeline(
        [MarkdownChunker(), RecursiveChunker(), FixedSizeChunker()],
        settings.DEFAULT_CHUNK_SIZE,
        settings.DEFAULT_CHUNK_OVERLAP,
    )
    return IndexingService(
        processing_repository=ProcessingRepository(db),
        indexing_repository=IndexingRepository(db),
        pipeline=pipeline,
        embedding_provider=DeterministicEmbeddingProvider(settings.EMBEDDING_DIMENSIONS, settings.EMBEDDING_MODEL),
        vector_store=QdrantVectorStore(settings.QDRANT_URL, settings.QDRANT_API_KEY),
        collection=settings.QDRANT_COLLECTION,
        batch_size=settings.INDEX_BATCH_SIZE,
    )


def get_indexing_service(db: DatabaseDep, settings: SettingsDep) -> IndexingService:
    return build_indexing_service(db, settings)


def build_processing_event_publisher(db, settings: Settings) -> ProcessingEventPublisher:
    if not settings.INDEXING_ENABLED:
        return NoOpProcessingEventPublisher()
    consumer = IndexingEventConsumer(build_indexing_service(db, settings))
    return SynchronousProcessingEventPublisher([consumer.handle])


IndexingServiceDep = Annotated[IndexingService, Depends(get_indexing_service)]
