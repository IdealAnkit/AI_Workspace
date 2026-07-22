"""Future queue adapter contract; no background worker is implemented in this phase."""

from abc import ABC, abstractmethod
from uuid import UUID


class IndexingWorker(ABC):
    @abstractmethod
    async def enqueue(self, processed_document_id: UUID) -> None: ...
