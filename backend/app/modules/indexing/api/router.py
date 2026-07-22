"""Read-only indexing state endpoints; indexing is event-driven only."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.modules.indexing.dependencies import IndexingServiceDep
from app.modules.indexing.schemas import IndexMetadataResponse
from app.schemas.responses import SuccessResponse
from app.utils.responses import ok

router = APIRouter()


@router.get(
    "/documents/{document_id}",
    response_model=SuccessResponse[IndexMetadataResponse],
    summary="Get latest document index metadata",
    description="Requires bearer authentication and ownership. This endpoint is read-only; indexing starts only from processing-completed events.",
)
async def get_document_index(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: IndexingServiceDep,
) -> SuccessResponse[IndexMetadataResponse]:
    metadata = await service.get_latest_index(document_id, current_user.id)
    return ok(data=IndexMetadataResponse.model_validate(metadata), message="Index metadata retrieved.")
