import time
from collections.abc import AsyncIterator
from uuid import UUID
from app.core.exceptions import NotFoundException
from app.modules.retrieval.retrievers.types import Query
from app.modules.chat.citations import CitationRenderer
from app.modules.chat.memory import ConversationMemory
from app.modules.chat.models import MessageRole
from app.modules.chat.prompting import PromptBuilder
from app.modules.chat.providers import BaseLLMProvider
from app.modules.chat.repositories import ChatRepository
from app.modules.chat.utils import NoOpValidator

class ChatService:
    def __init__(self, repository: ChatRepository, retrieval_service, provider: BaseLLMProvider, prompt_builder: PromptBuilder, memory: ConversationMemory, citation_renderer: CitationRenderer) -> None:
        self.repository, self.retrieval_service, self.provider, self.prompt_builder, self.memory, self.citation_renderer = repository, retrieval_service, provider, prompt_builder, memory, citation_renderer
        self.validator = NoOpValidator()
    async def create_conversation(self, user_id, workspace_id, title, metadata): return await self.repository.create_conversation(user_id, workspace_id, title, self.provider.provider_name(), self.provider.model_name(), metadata)
    async def conversation(self, conversation_id, user_id):
        item = await self.repository.get_conversation(conversation_id, user_id)
        if item is None: raise NotFoundException(message="Conversation not found.")
        return item
    async def send_message(self, conversation_id, user_id, content, document_ids, metadata):
        conversation = await self.conversation(conversation_id, user_id); self.validator.validate(content)
        await self.repository.create_message(conversation.id, MessageRole.USER, content, metadata=metadata)
        history = self.memory.recent(await self.repository.recent_messages(conversation.id, self.memory.max_messages))
        retrieval = await self.retrieval_service.search(Query(query=content, workspace_id=conversation.workspace_id, user_id=user_id, document_ids=document_ids, top_k=self.retrieval_service.default_top_k, score_threshold=self.retrieval_service.default_score_threshold))
        prompt = self.prompt_builder.build(history, retrieval.chunks, content)
        started = time.perf_counter(); response = await self.provider.generate(prompt.text); self.validator.validate(response)
        citations = self.citation_renderer.render(retrieval.citations)
        assistant = await self.repository.create_message(conversation.id, MessageRole.ASSISTANT, response, provider=self.provider.provider_name(), model=self.provider.model_name(), prompt_tokens=prompt.prompt_tokens, completion_tokens=len(response.split()), latency=time.perf_counter()-started, citations=citations, metadata={"prompt": prompt.metadata, "retrieval": retrieval.retrieval_metadata})
        await self.repository.record_assistant_metrics(conversation.id, assistant)
        return assistant, retrieval.retrieval_metadata
    async def stream_message(self, conversation_id, user_id, content, document_ids, metadata) -> AsyncIterator[dict]:
        conversation = await self.conversation(conversation_id, user_id); await self.repository.create_message(conversation.id, MessageRole.USER, content, metadata=metadata)
        history = self.memory.recent(await self.repository.recent_messages(conversation.id, self.memory.max_messages))
        retrieval = await self.retrieval_service.search(Query(query=content, workspace_id=conversation.workspace_id, user_id=user_id, document_ids=document_ids, top_k=self.retrieval_service.default_top_k, score_threshold=self.retrieval_service.default_score_threshold))
        prompt = self.prompt_builder.build(history, retrieval.chunks, content); output=[]; started=time.perf_counter()
        async for chunk in self.provider.stream(prompt.text): output.append(chunk); yield {"type":"chunk", "content":chunk}
        response="".join(output); citations=self.citation_renderer.render(retrieval.citations)
        assistant=await self.repository.create_message(conversation.id, MessageRole.ASSISTANT, response, provider=self.provider.provider_name(), model=self.provider.model_name(), prompt_tokens=prompt.prompt_tokens, completion_tokens=len(response.split()), latency=time.perf_counter()-started, citations=citations, metadata={"prompt":prompt.metadata,"retrieval":retrieval.retrieval_metadata})
        await self.repository.record_assistant_metrics(conversation.id, assistant); yield {"type":"complete", "message_id":str(assistant.id), "citations":citations}
