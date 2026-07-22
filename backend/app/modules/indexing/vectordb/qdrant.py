"""Qdrant implementation kept behind the vector-store contract."""

from typing import Any

from app.modules.indexing.vectordb.base import BaseVectorStore, VectorRecord


class QdrantVectorStore(BaseVectorStore):
    """Async Qdrant adapter. A fake client can be injected for offline tests."""

    def __init__(self, url: str, api_key: str = "", client: Any | None = None) -> None:
        if client is None:
            from qdrant_client import AsyncQdrantClient

            client = AsyncQdrantClient(url=url, api_key=api_key or None)
        self.client = client

    async def collection_exists(self, name: str) -> bool:
        return bool(await self.client.collection_exists(name))

    async def create_collection(self, name: str, dimensions: int) -> None:
        if await self.collection_exists(name):
            return
        from qdrant_client.models import Distance, VectorParams

        await self.client.create_collection(collection_name=name, vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE))

    async def upsert(self, collection: str, records: list[VectorRecord]) -> None:
        if not records:
            return
        from qdrant_client.models import PointStruct

        points = [PointStruct(id=record.id, vector=record.vector, payload=record.payload) for record in records]
        await self.client.upsert(collection_name=collection, points=points, wait=True)

    async def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return
        from qdrant_client.models import PointIdsList

        await self.client.delete(collection_name=collection, points_selector=PointIdsList(points=ids), wait=True)

    async def search(self, collection: str, vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        results = await self.client.query_points(collection_name=collection, query=vector, limit=limit, with_payload=True)
        return [{"id": str(point.id), "score": point.score, "payload": point.payload or {}} for point in results.points]

    async def delete_document(self, collection: str, document_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        selector = FilterSelector(filter=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]))
        await self.client.delete(collection_name=collection, points_selector=selector, wait=True)
