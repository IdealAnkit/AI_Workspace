"""Provider-neutral vector store contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: list[float]
    payload: dict[str, Any]


class BaseVectorStore(ABC):
    @abstractmethod
    async def create_collection(self, name: str, dimensions: int) -> None: ...

    @abstractmethod
    async def upsert(self, collection: str, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> None: ...

    @abstractmethod
    async def search(self, collection: str, vector: list[float], limit: int = 10) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def delete_document(self, collection: str, document_id: str) -> None: ...

    @abstractmethod
    async def collection_exists(self, name: str) -> bool: ...
