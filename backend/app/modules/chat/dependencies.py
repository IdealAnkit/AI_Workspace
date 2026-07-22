from typing import Annotated
from fastapi import Depends
from app.api.deps import DatabaseDep, SettingsDep
from app.modules.chat.citations import CitationRenderer
from app.modules.chat.memory import ConversationMemory
from app.modules.chat.prompting import PromptBuilder
from app.modules.chat.providers import MockLLMProvider
from app.modules.chat.repositories import ChatRepository
from app.modules.chat.services import ChatService
from app.modules.retrieval.dependencies import get_retrieval_service

def get_chat_service(db: DatabaseDep, settings: SettingsDep) -> ChatService:
    if settings.LLM_PROVIDER != "mock": raise ValueError("Only MockLLMProvider is available in this phase.")
    return ChatService(ChatRepository(db), get_retrieval_service(db, settings), MockLLMProvider(settings.LLM_MODEL, settings.LLM_MAX_TOKENS), PromptBuilder(settings.SYSTEM_PROMPT, settings.LLM_MAX_TOKENS), ConversationMemory(settings.MAX_HISTORY_MESSAGES if settings.ENABLE_CHAT_HISTORY else 0), CitationRenderer())
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
