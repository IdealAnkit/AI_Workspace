"""Offline deterministic embedder for development and tests only."""

import hashlib

from app.modules.indexing.embedders.base import BaseEmbeddingProvider


class DeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """Generate stable normalized vectors from SHA-256 digests without network calls."""

    def __init__(self, dimensions: int, model: str = "deterministic-v1") -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive.")
        self._dimensions = dimensions
        self._model = model

    async def embed(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self._dimensions:
            digest = hashlib.sha256(f"{self._model}:{counter}:{text}".encode("utf-8")).digest()
            values.extend((byte / 127.5) - 1.0 for byte in digest)
            counter += 1
        vector = values[: self._dimensions]
        magnitude = sum(value * value for value in vector) ** 0.5
        return [value / magnitude for value in vector] if magnitude else vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]

    def dimensions(self) -> int:
        return self._dimensions

    def model_name(self) -> str:
        return self._model

    def provider_name(self) -> str:
        return "deterministic"
