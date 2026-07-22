"""Authenticated retrieval-only endpoints. No LLM answers are generated."""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.modules.retrieval.dependencies import RetrievalServiceDep
from app.modules.retrieval.retrievers.types import Query as RetrievalQuery
from app.modules.retrieval.schemas import QueryHistoryResponse, RetrievalResultResponse, RetrievalSearchRequest, SearchAnalyticsResponse
from app.schemas.responses import PaginatedResponse, SuccessResponse
from app.utils.pagination import compute_pagination, get_offset
from app.utils.responses import ok, paginated

router = APIRouter()


@router.post("/search", response_model=SuccessResponse[RetrievalResultResponse], summary="Retrieve indexed document chunks", description="Requires bearer authentication. Returns chunks, context metadata, and citations only; it does not call an LLM or generate an answer.")
async def search(payload: RetrievalSearchRequest, current_user: CurrentUserDep, service: RetrievalServiceDep) -> SuccessResponse[RetrievalResultResponse]:
    query = RetrievalQuery(query=payload.query, workspace_id=payload.workspace_id, user_id=current_user.id, document_ids=payload.document_ids, language=payload.language, filters=payload.filters, top_k=payload.top_k or service.default_top_k, metadata=payload.metadata, future_options=payload.future_options, timestamp=datetime.now(UTC), score_threshold=payload.score_threshold if payload.score_threshold is not None else service.default_score_threshold)
    result = await service.search(query)
    chunks = []
    for chunk, citation in zip(result.chunks, result.citations):
        chunks.append({"id": chunk.id, "document_id": chunk.document_id, "chunk_index": chunk.chunk_index, "text": chunk.text, "score": chunk.score, "source": chunk.source, "page_start": chunk.page_start, "page_end": chunk.page_end, "section_title": chunk.section_title, "metadata": chunk.metadata, "ranking_metadata": chunk.ranking_metadata, "citation": citation})
    return ok(data=RetrievalResultResponse(query=result.query, normalized_query=result.normalized_query, retriever=result.retriever, chunks=chunks, search_statistics=result.search_statistics, retrieval_metadata=result.retrieval_metadata, duration_seconds=result.duration_seconds), message="Retrieval completed.")


@router.get("/history", response_model=PaginatedResponse[QueryHistoryResponse], summary="List retrieval history")
async def history(current_user: CurrentUserDep, service: RetrievalServiceDep, page: int = Query(DEFAULT_PAGE, ge=1), size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)) -> PaginatedResponse[QueryHistoryResponse]:
    items, total = await service.history(current_user.id, get_offset(page, size), size)
    return paginated(data=[QueryHistoryResponse.model_validate(item) for item in items], pagination=compute_pagination(total, page, size), message="Retrieval history retrieved.")


@router.get("/history/{history_id}", response_model=SuccessResponse[QueryHistoryResponse], summary="Get one retrieval history record")
async def get_history(history_id: UUID, current_user: CurrentUserDep, service: RetrievalServiceDep) -> SuccessResponse[QueryHistoryResponse]:
    return ok(data=QueryHistoryResponse.model_validate(await service.get_history(history_id, current_user.id)), message="Retrieval history retrieved.")


@router.get("/analytics", response_model=SuccessResponse[SearchAnalyticsResponse], summary="Get personal retrieval analytics")
async def analytics(current_user: CurrentUserDep, service: RetrievalServiceDep) -> SuccessResponse[SearchAnalyticsResponse]:
    total, average, chunks = await service.analytics(current_user.id)
    return ok(data=SearchAnalyticsResponse(total_searches=total, average_duration_seconds=average, total_returned_chunks=chunks), message="Retrieval analytics retrieved.")
