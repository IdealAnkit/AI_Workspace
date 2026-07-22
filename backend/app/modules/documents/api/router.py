"""Authenticated document metadata and storage endpoints."""

from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from app.api.deps import CurrentUserDep
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.modules.documents.dependencies import DocumentServiceDep
from app.modules.documents.schemas.document import DocumentResponse, SignedDownloadResponse
from app.modules.documents.services.document_service import SignedDocumentDownload
from app.schemas.responses import PaginatedResponse, SuccessResponse
from app.utils.pagination import compute_pagination
from app.utils.responses import created, ok, paginated

router = APIRouter()


@router.post(
    "/upload",
    response_model=SuccessResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description=(
        "Requires bearer authentication. Upload one PDF, DOCX, TXT, or Markdown document. "
        "The default maximum is 25 MiB and is configurable with DOCUMENT_MAX_FILE_SIZE_BYTES."
    ),
    responses={
        201: {
            "description": "Document stored successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Document uploaded successfully.",
                        "data": {
                            "id": "b251a41d-73a1-451f-b8c3-55ceef4e7f08",
                            "filename": "architecture-overview.pdf",
                            "mime_type": "application/pdf",
                            "size_bytes": 248921,
                            "status": "stored",
                            "upload_status": "stored",
                            "version": 1,
                            "is_latest_version": True,
                        },
                    }
                }
            },
        }
    },
)
async def upload_document(
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    file: UploadFile = File(
        ...,
        description="PDF, DOCX, TXT, or Markdown file. Default limit: 25 MiB; configurable server-side.",
    ),
) -> SuccessResponse[DocumentResponse]:
    """Upload a document and persist only its metadata in PostgreSQL."""
    document = await service.upload(file, current_user)
    return created(data=DocumentResponse.model_validate(document), message="Document uploaded successfully.")


@router.get(
    "/{document_id}",
    response_model=SuccessResponse[DocumentResponse],
    summary="Get document metadata",
)
async def get_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> SuccessResponse[DocumentResponse]:
    """Get metadata for one document owned by the authenticated user."""
    document = await service.get(document_id, current_user.id)
    return ok(data=DocumentResponse.model_validate(document), message="Document retrieved.")


@router.get(
    "",
    response_model=PaginatedResponse[DocumentResponse],
    summary="List documents",
    description="Requires bearer authentication. Soft-deleted documents are never returned.",
)
async def list_documents(
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    page: int = Query(DEFAULT_PAGE, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PaginatedResponse[DocumentResponse]:
    """List the authenticated user's document metadata in newest-first order."""
    result = await service.list(current_user.id, page, size)
    return paginated(
        data=[DocumentResponse.model_validate(document) for document in result.documents],
        pagination=compute_pagination(total=result.total, page=page, size=size),
        message="Documents retrieved.",
    )


@router.delete(
    "/{document_id}",
    response_model=SuccessResponse[None],
    summary="Delete a document",
    description="Requires bearer authentication. Soft-deletes metadata and optionally removes provider bytes.",
)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> SuccessResponse[None]:
    """Delete both provider bytes and metadata for one owned document."""
    await service.delete(document_id, current_user.id)
    return ok(message="Document deleted successfully.")


@router.get(
    "/{document_id}/download",
    response_class=StreamingResponse,
    response_model=None,
    summary="Download a document",
    description=(
        "Requires bearer authentication. Defaults to a streamed response for backward compatibility. "
        "Use delivery=signed to request a provider-signed URL, or delivery=auto to prefer one."
    ),
    responses={
        200: {
            "description": "Document stream or signed download URL.",
            "content": {
                "application/octet-stream": {},
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Signed download URL created.",
                        "data": {
                            "document_id": "b251a41d-73a1-451f-b8c3-55ceef4e7f08",
                            "download_url": "https://storage.example/documents/...signature...",
                            "expires_in_seconds": 900,
                        },
                    }
                },
            },
        }
    },
)
async def download_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    delivery: str = Query("stream", pattern="^(stream|signed|auto)$"),
) -> StreamingResponse | SuccessResponse[SignedDownloadResponse]:
    """Stream an owned document without exposing its internal storage key."""
    result = await service.download(document_id, current_user.id, delivery)
    if isinstance(result, SignedDocumentDownload):
        signed_response = ok(
            data=SignedDownloadResponse(
                document_id=result.document.id,
                download_url=result.url,
                expires_in_seconds=result.expires_in_seconds,
            ),
            message="Signed download URL created.",
        )
        return JSONResponse(content=signed_response.model_dump(mode="json"))
    content_disposition = f"attachment; filename*=UTF-8''{quote(result.document.filename, safe='')}"
    return StreamingResponse(
        result.storage_download.chunks,
        media_type=result.document.mime_type,
        headers={
            "Content-Disposition": content_disposition,
            "Content-Length": str(result.document.size_bytes),
        },
        background=BackgroundTask(result.storage_download.close),
    )
