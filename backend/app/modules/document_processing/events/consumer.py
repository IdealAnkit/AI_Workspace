"""Consume document lifecycle events without binding to a message broker."""

from app.modules.documents.events.base import DocumentDeletedEvent, DocumentUploadedEvent
from app.modules.document_processing.services.processing_service import ProcessingService


class DocumentProcessingEventConsumer:
    """Start synchronous processing when newly stored documents are announced."""

    def __init__(self, processing_service: ProcessingService) -> None:
        self.processing_service = processing_service

    async def handle(self, event: DocumentUploadedEvent | DocumentDeletedEvent) -> None:
        if isinstance(event, DocumentUploadedEvent):
            await self.processing_service.process_document(event.document_id)
