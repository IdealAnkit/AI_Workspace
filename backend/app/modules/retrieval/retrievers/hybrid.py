from app.modules.retrieval.retrievers.base import BaseRetriever
from app.modules.retrieval.retrievers.types import Query, RetrievedChunk


class HybridRetriever(BaseRetriever):
    def __init__(self, semantic: BaseRetriever, keyword: BaseRetriever, semantic_weight: float, keyword_weight: float) -> None:
        self.semantic, self.keyword, self.semantic_weight, self.keyword_weight = semantic, keyword, semantic_weight, keyword_weight
    def supports(self, query: Query) -> bool: return self.semantic.supports(query) and self.keyword.supports(query)
    def name(self) -> str: return "hybrid"
    async def retrieve(self, query: Query) -> list[RetrievedChunk]:
        semantic, keyword = await self.semantic.retrieve(query), await self.keyword.retrieve(query)
        merged: dict = {}
        for items, weight in ((semantic, self.semantic_weight), (keyword, self.keyword_weight)):
            max_score = max((item.score for item in items), default=1.0) or 1.0
            for item in items:
                existing = merged.get(item.id)
                contribution = weight * (item.score / max_score)
                source = item.source
                if existing is None:
                    item.score = contribution; item.source = self.name(); item.ranking_metadata = {"fusion": {source: contribution}}; merged[item.id] = item
                else:
                    existing.score += contribution; existing.ranking_metadata.setdefault("fusion", {})[source] = contribution
        return list(merged.values())
