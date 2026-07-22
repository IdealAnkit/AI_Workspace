"""Embedding provider contracts; no external model is required in this phase."""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def dimensions(self) -> int: ...

    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    def provider_name(self) -> str: ...
