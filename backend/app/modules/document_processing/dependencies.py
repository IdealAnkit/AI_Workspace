"""Dependency wiring for document-processing orchestration and read APIs."""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DatabaseDep, SettingsDep
from app.config.settings import Settings
from app.modules.documents.events.base import DocumentEventPublisher, SynchronousDocumentEventPublisher
from app.modules.documents.repositories.document_repository import DocumentRepository
from app.modules.documents.storage.manager import StorageManager
from app.modules.document_processing.events.consumer import DocumentProcessingEventConsumer
from app.modules.document_processing.extractors.metadata import MetadataExtractor
from app.modules.document_processing.parsers.docx_parser import DocxParser
from app.modules.document_processing.parsers.markdown_parser import MarkdownParser
from app.modules.document_processing.parsers.pdf_parser import PdfParser
from app.modules.document_processing.parsers.registry import ParserRegistry
from app.modules.document_processing.parsers.txt_parser import TextParser
from app.modules.document_processing.pipeline.pipeline import DocumentProcessingPipeline
from app.modules.document_processing.processors.normalizer import TextNormalizer
from app.modules.document_processing.repositories.processing_repository import ProcessingRepository
from app.modules.document_processing.services.content_reader import StorageManagerContentReader
from app.modules.document_processing.services.processing_service import ProcessingService


def build_processing_service(db, settings: Settings) -> ProcessingService:
    """Build a request-scoped service without coupling the pipeline to a provider."""
    from app.modules.indexing.dependencies import build_processing_event_publisher

    registry = ParserRegistry([PdfParser(), TextParser(), MarkdownParser(), DocxParser()])
    pipeline = DocumentProcessingPipeline(
        registry,
        TextNormalizer(),
        MetadataExtractor(),
        max_content_bytes=settings.DOCUMENT_PROCESSING_MAX_CONTENT_BYTES,
    )
    storage_manager = StorageManager.from_settings(settings)
    return ProcessingService(
        document_repository=DocumentRepository(db),
        processing_repository=ProcessingRepository(db),
        content_reader=StorageManagerContentReader(storage_manager),
        pipeline=pipeline,
        event_publisher=build_processing_event_publisher(db, settings),
    )


def get_processing_service(db: DatabaseDep, settings: SettingsDep) -> ProcessingService:
    """Provide processing APIs with a request-scoped database session."""
    return build_processing_service(db, settings)


def get_document_event_publisher(
    db: DatabaseDep, settings: SettingsDep
) -> DocumentEventPublisher:
    """Wire document-upload events to the synchronous Phase 4 processing consumer."""
    consumer = DocumentProcessingEventConsumer(build_processing_service(db, settings))
    return SynchronousDocumentEventPublisher([consumer.handle])


ProcessingServiceDep = Annotated[ProcessingService, Depends(get_processing_service)]
