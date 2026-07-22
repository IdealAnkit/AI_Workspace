from abc import ABC, abstractmethod

from app.modules.retrieval.retrievers.types import Query, RetrievedChunk


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: Query) -> list[RetrievedChunk]: ...

    @abstractmethod
    def supports(self, query: Query) -> bool: ...

    @abstractmethod
    def name(self) -> str: ...
