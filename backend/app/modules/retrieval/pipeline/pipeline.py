import time
from dataclasses import dataclass
from typing import Any

from app.modules.retrieval.citations import CitationBuilder
from app.modules.retrieval.context import ContextBuilder
from app.modules.retrieval.filters import FilterPipeline
from app.modules.retrieval.rankers import BaseRanker
from app.modules.retrieval.retrievers import BaseRetriever
from app.modules.retrieval.retrievers.types import Query, RetrievedChunk
from app.modules.retrieval.utils import QueryNormalizer


@dataclass
class RetrievalResult:
    query: str
    normalized_query: str
    retriever: str
    chunks: list[RetrievedChunk]
    citations: list[dict[str, Any]]
    search_statistics: dict[str, Any]
    retrieval_metadata: dict[str, Any]
    duration_seconds: float


class RetrievalPipeline:
    def __init__(self, normalizer: QueryNormalizer, filters: FilterPipeline, retriever: BaseRetriever, ranker: BaseRanker, context_builder: ContextBuilder, citation_builder: CitationBuilder) -> None:
        self.normalizer, self.filters, self.retriever, self.ranker, self.context_builder, self.citation_builder = normalizer, filters, retriever, ranker, context_builder, citation_builder
    async def run(self, query: Query) -> RetrievalResult:
        started = time.perf_counter(); normalized = self.normalizer.normalize(query.query)
        query = Query(**{**query.__dict__, "query": normalized})
        candidates = await self.retriever.retrieve(query)
        filtered = self.filters.apply(candidates, query)
        ranked = self.ranker.rank(filtered, query)
        context = self.context_builder.build(ranked[: query.top_k])
        return RetrievalResult(query=query.query, normalized_query=normalized, retriever=self.retriever.name(), chunks=context, citations=[self.citation_builder.build(item) for item in context], search_statistics={"candidate_count": len(candidates), "filtered_count": len(filtered), "returned_chunks": len(context)}, retrieval_metadata={"score_threshold": query.score_threshold, "filters": query.filters}, duration_seconds=time.perf_counter() - started)
