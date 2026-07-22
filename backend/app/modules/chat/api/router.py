from uuid import UUID
from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse
from app.api.deps import CurrentUserDep
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.modules.chat.dependencies import ChatServiceDep
from app.modules.chat.schemas import ChatResponse, ConversationResponse, CreateConversationRequest, MessageResponse, SendMessageRequest
from app.modules.chat.streaming import sse
from app.schemas.responses import PaginatedResponse, SuccessResponse
from app.utils.pagination import compute_pagination, get_offset
from app.utils.responses import created, ok, paginated

router=APIRouter()
@router.post("/conversations", response_model=SuccessResponse[ConversationResponse], status_code=status.HTTP_201_CREATED, summary="Create a chat conversation")
async def create_conversation(payload: CreateConversationRequest, current_user: CurrentUserDep, service: ChatServiceDep): return created(data=ConversationResponse.model_validate(await service.create_conversation(current_user.id,payload.workspace_id,payload.title,payload.metadata)), message="Conversation created.")
@router.get("/conversations", response_model=PaginatedResponse[ConversationResponse], summary="List conversations")
async def conversations(current_user: CurrentUserDep, service: ChatServiceDep, page:int=Query(DEFAULT_PAGE,ge=1), size:int=Query(DEFAULT_PAGE_SIZE,ge=1,le=MAX_PAGE_SIZE)):
    items,total=await service.repository.list_conversations(current_user.id,get_offset(page,size),size); return paginated([ConversationResponse.model_validate(x) for x in items],compute_pagination(total,page,size),"Conversations retrieved.")
@router.get("/conversations/{conversation_id}", response_model=SuccessResponse[ConversationResponse], summary="Get conversation")
async def conversation(conversation_id:UUID,current_user:CurrentUserDep,service:ChatServiceDep): return ok(data=ConversationResponse.model_validate(await service.conversation(conversation_id,current_user.id)),message="Conversation retrieved.")
@router.post("/conversations/{conversation_id}/messages", response_model=SuccessResponse[ChatResponse], summary="Send a message and receive a chat response", description="Uses retrieval context and the configured mock provider; citations are reused from retrieval.")
async def message(conversation_id:UUID,payload:SendMessageRequest,current_user:CurrentUserDep,service:ChatServiceDep):
    item,meta=await service.send_message(conversation_id,current_user.id,payload.content,payload.document_ids,payload.metadata); return ok(data=ChatResponse(message=MessageResponse.model_validate(item),retrieval_metadata=meta),message="Chat response generated.")
@router.get("/conversations/{conversation_id}/messages",response_model=PaginatedResponse[MessageResponse],summary="List conversation messages")
async def messages(conversation_id:UUID,current_user:CurrentUserDep,service:ChatServiceDep,page:int=Query(DEFAULT_PAGE,ge=1),size:int=Query(DEFAULT_PAGE_SIZE,ge=1,le=MAX_PAGE_SIZE)):
    await service.conversation(conversation_id,current_user.id); items,total=await service.repository.list_messages(conversation_id,get_offset(page,size),size); return paginated([MessageResponse.model_validate(x) for x in items],compute_pagination(total,page,size),"Messages retrieved.")
@router.delete("/conversations/{conversation_id}",response_model=SuccessResponse[None],summary="Delete conversation")
async def delete(conversation_id:UUID,current_user:CurrentUserDep,service:ChatServiceDep): await service.repository.delete_conversation(await service.conversation(conversation_id,current_user.id)); return ok(message="Conversation deleted.")
@router.post("/conversations/{conversation_id}/stream",response_class=StreamingResponse,response_model=None,summary="Stream a chat response",description="Server-Sent Events: chunk events followed by a complete event containing retrieval citations.")
async def stream(conversation_id:UUID,payload:SendMessageRequest,current_user:CurrentUserDep,service:ChatServiceDep):
    async def events():
        async for event in service.stream_message(conversation_id,current_user.id,payload.content,payload.document_ids,payload.metadata): yield sse(event.pop("type"),event)
    return StreamingResponse(events(),media_type="text/event-stream")
