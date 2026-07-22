"""Future retrieval worker contract; synchronous API execution is used today."""

from abc import ABC, abstractmethod
from uuid import UUID


class RetrievalWorker(ABC):
    @abstractmethod
    async def enqueue(self, retrieval_session_id: UUID) -> None: ...
