"""Worker abstraction reserved for future asynchronous processing implementations."""

from abc import ABC, abstractmethod
from uuid import UUID


class ProcessingWorker(ABC):
    """Future Celery, Arq, RQ, or Temporal adapters implement this contract."""

    @abstractmethod
    async def enqueue(self, document_id: UUID) -> None:
        """Schedule a document without exposing a concrete background runtime."""
