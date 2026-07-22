"""Synchronously consume successful processing events."""

from app.modules.document_processing.events.base import ProcessingCompletedEvent
from app.modules.indexing.services import IndexingService


class IndexingEventConsumer:
    def __init__(self, indexing_service: IndexingService) -> None:
        self.indexing_service = indexing_service

    async def handle(self, event: ProcessingCompletedEvent) -> None:
        await self.indexing_service.index_processed_document(event.processed_document_id)
