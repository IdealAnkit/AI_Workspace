"""Processing lifecycle events with transport-independent synchronous dispatch."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProcessingCompletedEvent:
    processed_document_id: UUID
    document_id: UUID
    processing_job_id: UUID | None
    owner_id: UUID
    occurred_at: datetime


class ProcessingEventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: ProcessingCompletedEvent) -> None: ...


class NoOpProcessingEventPublisher(ProcessingEventPublisher):
    async def publish(self, event: ProcessingCompletedEvent) -> None:
        return None


ProcessingEventHandler = Callable[[ProcessingCompletedEvent], Awaitable[None]]


class SynchronousProcessingEventPublisher(ProcessingEventPublisher):
    def __init__(self, handlers: list[ProcessingEventHandler] | None = None) -> None:
        self.handlers = handlers or []

    async def publish(self, event: ProcessingCompletedEvent) -> None:
        for handler in self.handlers:
            await handler(event)
