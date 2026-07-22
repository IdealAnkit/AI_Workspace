"""Authenticated, read-only visibility into document processing."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.modules.document_processing.dependencies import ProcessingServiceDep
from app.modules.document_processing.schemas.processing import (
    DocumentProcessingResponse,
    ProcessingJobResponse,
    ProcessingLogResponse,
    ProcessedDocumentResponse,
)
from app.schemas.responses import PaginatedResponse, SuccessResponse
from app.utils.pagination import compute_pagination
from app.utils.responses import ok, paginated

processing_router = APIRouter()
document_processing_router = APIRouter()


@processing_router.get(
    "/jobs",
    response_model=PaginatedResponse[ProcessingJobResponse],
    summary="List document processing jobs",
    description="Requires bearer authentication. Returns jobs only for documents owned by the current user.",
)
async def list_processing_jobs(
    current_user: CurrentUserDep,
    service: ProcessingServiceDep,
    page: int = Query(DEFAULT_PAGE, ge=1, description="One-indexed result page."),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Jobs per page."),
) -> PaginatedResponse[ProcessingJobResponse]:
    """List processing attempts newest first; this endpoint never starts processing."""
    offset = (page - 1) * size
    jobs, total = await service.list_jobs(current_user.id, offset, size)
    return paginated(
        data=[ProcessingJobResponse.model_validate(job) for job in jobs],
        pagination=compute_pagination(total=total, page=page, size=size),
        message="Processing jobs retrieved.",
    )


@processing_router.get(
    "/jobs/{job_id}",
    response_model=SuccessResponse[ProcessingJobResponse],
    summary="Get a document processing job",
    description="Requires bearer authentication and ownership of the associated document.",
)
async def get_processing_job(
    job_id: UUID,
    current_user: CurrentUserDep,
    service: ProcessingServiceDep,
) -> SuccessResponse[ProcessingJobResponse]:
    """Return one durable processing attempt."""
    job = await service.get_job(job_id, current_user.id)
    return ok(data=ProcessingJobResponse.model_validate(job), message="Processing job retrieved.")


@processing_router.get(
    "/jobs/{job_id}/logs",
    response_model=SuccessResponse[list[ProcessingLogResponse]],
    summary="Get processing job logs",
    description="Requires bearer authentication and ownership of the associated document.",
)
async def get_processing_job_logs(
    job_id: UUID,
    current_user: CurrentUserDep,
    service: ProcessingServiceDep,
) -> SuccessResponse[list[ProcessingLogResponse]]:
    """Return persisted log entries after owner authorization."""
    logs = await service.get_logs(job_id, current_user.id)
    return ok(
        data=[ProcessingLogResponse.model_validate(log) for log in logs],
        message="Processing logs retrieved.",
    )


@document_processing_router.get(
    "/{document_id}/processing",
    response_model=SuccessResponse[DocumentProcessingResponse],
    summary="Get a document's processing result",
    description=(
        "Requires bearer authentication and document ownership. Processing begins automatically after upload; "
        "this endpoint is read-only and does not initiate work."
    ),
    responses={
        200: {
            "description": "Current job and the normalized result when available.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Document processing state retrieved.",
                        "data": {
                            "job": {"status": "completed", "attempts": 1},
                            "result": {
                                "title": "Architecture Overview",
                                "page_count": 3,
                                "text": "Normalized document text...",
                                "metadata": {"word_count": 420},
                            },
                        },
                    }
                }
            },
        }
    },
)
async def get_document_processing(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: ProcessingServiceDep,
) -> SuccessResponse[DocumentProcessingResponse]:
    """Return the latest job and persisted normalized extraction for one owned document."""
    overview = await service.get_document_overview(document_id, current_user.id)
    response = DocumentProcessingResponse(
        job=ProcessingJobResponse.model_validate(overview.job) if overview.job else None,
        result=ProcessedDocumentResponse.model_validate(overview.result) if overview.result else None,
    )
    return ok(data=response, message="Document processing state retrieved.")
