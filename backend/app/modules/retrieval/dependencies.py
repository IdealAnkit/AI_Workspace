from typing import Annotated

from fastapi import Depends

from app.api.deps import DatabaseDep, SettingsDep
from app.modules.indexing.embedders import DeterministicEmbeddingProvider
from app.modules.indexing.vectordb import QdrantVectorStore
from app.modules.retrieval.citations import CitationBuilder
from app.modules.retrieval.context import ContextBuilder
from app.modules.retrieval.filters import DateFilter, DocumentFilter, FilterPipeline, LanguageFilter, MetadataFilter, OwnerFilter, TagFilter, WorkspaceFilter
from app.modules.retrieval.pipeline import RetrievalPipeline
from app.modules.retrieval.rankers import DefaultScoreRanker
from app.modules.retrieval.repositories import RetrievalRepository
from app.modules.retrieval.retrievers import HybridRetriever, KeywordRetriever, SemanticRetriever
from app.modules.retrieval.services import RetrievalService
from app.modules.retrieval.utils import QueryNormalizer


def get_retrieval_service(db: DatabaseDep, settings: SettingsDep) -> RetrievalService:
    repository = RetrievalRepository(db)
    semantic = SemanticRetriever(QdrantVectorStore(settings.QDRANT_URL, settings.QDRANT_API_KEY), DeterministicEmbeddingProvider(settings.EMBEDDING_DIMENSIONS, settings.EMBEDDING_MODEL), repository, settings.QDRANT_COLLECTION)
    keyword = KeywordRetriever(repository)
    retriever = HybridRetriever(semantic, keyword, settings.SEMANTIC_WEIGHT, settings.KEYWORD_WEIGHT) if settings.ENABLE_HYBRID_SEARCH else semantic
    pipeline = RetrievalPipeline(QueryNormalizer(), FilterPipeline([OwnerFilter(), WorkspaceFilter(), DocumentFilter(), MetadataFilter(), LanguageFilter(), DateFilter(), TagFilter()]), retriever, DefaultScoreRanker(), ContextBuilder(settings.MAX_CONTEXT_TOKENS), CitationBuilder())
    return RetrievalService(repository, pipeline, settings.DEFAULT_TOP_K, settings.MAX_TOP_K, settings.DEFAULT_SCORE_THRESHOLD)


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]
