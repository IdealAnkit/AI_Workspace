from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.chat.models import ChatLog, Conversation, ConversationMetadata, ConversationStatistics, Message, MessageRole, TokenUsage

class ChatRepository:
    def __init__(self, session: AsyncSession) -> None: self.session = session
    async def create_conversation(self, user_id: UUID, workspace_id: UUID | None, title: str, provider: str, model: str, metadata: dict) -> Conversation:
        item = Conversation(user_id=user_id, workspace_id=workspace_id, title=title, provider=provider, model=model)
        self.session.add(item); await self.session.flush(); await self.session.refresh(item)
        self.session.add_all([ConversationMetadata(conversation_id=item.id, metadata_=metadata), ConversationStatistics(conversation_id=item.id)])
        await self.session.flush(); return item
    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        result = await self.session.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)); return result.scalar_one_or_none()
    async def list_conversations(self, user_id: UUID, offset: int, limit: int):
        result = await self.session.execute(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).offset(offset).limit(limit))
        total = await self.session.execute(select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id))
        return list(result.scalars().all()), int(total.scalar_one())
    async def delete_conversation(self, item: Conversation) -> None: await self.session.delete(item); await self.session.flush()
    async def create_message(self, conversation_id: UUID, role: MessageRole, content: str, *, provider=None, model=None, prompt_tokens=0, completion_tokens=0, latency=None, citations=None, metadata=None) -> Message:
        item = Message(conversation_id=conversation_id, role=role.value, content=content, provider=provider, model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, latency_seconds=latency, citations=citations or [], metadata_=metadata or {})
        self.session.add(item); await self.session.flush(); await self.session.refresh(item); return item
    async def recent_messages(self, conversation_id: UUID, limit: int) -> list[Message]:
        result = await self.session.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).limit(limit)); return list(result.scalars().all())
    async def list_messages(self, conversation_id: UUID, offset: int, limit: int):
        result = await self.session.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).offset(offset).limit(limit))
        total = await self.session.execute(select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id))
        return list(result.scalars().all()), int(total.scalar_one())
    async def record_assistant_metrics(self, conversation_id: UUID, message: Message) -> None:
        stats = (await self.session.execute(select(ConversationStatistics).where(ConversationStatistics.conversation_id == conversation_id))).scalar_one()
        stats.message_count += 1; stats.prompt_tokens += message.prompt_tokens; stats.completion_tokens += message.completion_tokens
        self.session.add(TokenUsage(message_id=message.id, provider=message.provider or "mock", model=message.model or "mock", prompt_tokens=message.prompt_tokens, completion_tokens=message.completion_tokens))
        self.session.add(ChatLog(conversation_id=conversation_id, level="INFO", message="Assistant response generated.")); await self.session.flush()
    async def add_log(self, conversation_id: UUID, level: str, message: str) -> None:
        self.session.add(ChatLog(conversation_id=conversation_id, level=level, message=message)); await self.session.flush()
