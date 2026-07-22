from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.chat.models import MessageRole

class CreateConversationRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=255, examples=["Document architecture review"])
    workspace_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000, examples=["How is indexing triggered?"])
    document_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; title: str; workspace_id: UUID | None; provider: str; model: str; created_at: datetime; updated_at: datetime
class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; conversation_id: UUID; role: MessageRole; content: str; provider: str | None; model: str | None; prompt_tokens: int; completion_tokens: int; latency_seconds: float | None; citations: list[dict[str, Any]]; metadata: dict[str, Any] = Field(validation_alias="metadata_"); created_at: datetime
class ChatResponse(BaseModel):
    message: MessageResponse
    retrieval_metadata: dict[str, Any]
