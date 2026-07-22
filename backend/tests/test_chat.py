"""Offline tests for chat orchestration, SSE, prompts, and citations."""
import unittest, uuid
from types import SimpleNamespace
from datetime import UTC, datetime
from fastapi.testclient import TestClient
from app.api.deps import get_current_user
from app.core.app_factory import create_app
from app.models.user import User
from app.modules.chat.citations import CitationRenderer
from app.modules.chat.dependencies import get_chat_service
from app.modules.chat.memory import ConversationMemory
from app.modules.chat.models import MessageRole
from app.modules.chat.prompting import PromptBuilder
from app.modules.chat.providers import MockLLMProvider
from app.modules.chat.services import ChatService
from app.modules.retrieval.pipeline import RetrievalResult

class PromptProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_prompt_budget_mock_provider_and_streaming(self):
        history=[SimpleNamespace(role="user",content="old question"),SimpleNamespace(role="assistant",content="old answer")]
        context=[SimpleNamespace(text="source context")]
        prompt=PromptBuilder("System instructions",20).build(history,context,"What happened?")
        provider=MockLLMProvider()
        response=await provider.generate(prompt.text); chunks=[x async for x in provider.stream(prompt.text)]
        self.assertIn("What happened?",response);self.assertEqual(response,"".join(chunks).strip());self.assertLessEqual(prompt.prompt_tokens,20)
    def test_history_zero_window(self): self.assertEqual(ConversationMemory(0).recent([1,2]),[])

class MemoryRepository:
    def __init__(self): self.messages=[];self.conversation=SimpleNamespace(id=uuid.uuid4(),workspace_id=None)
    async def create_conversation(self,*args): return self.conversation
    async def get_conversation(self,*args): return self.conversation
    async def create_message(self,conversation_id,role,content,**kwargs):
        item=SimpleNamespace(id=uuid.uuid4(),conversation_id=conversation_id,role=role.value,content=content,**kwargs);self.messages.append(item);return item
    async def recent_messages(self,*args): return self.messages
    async def record_assistant_metrics(self,*args): return None

class FakeRetrieval:
    default_top_k=4;default_score_threshold=0.0
    async def search(self,query):
        chunk=SimpleNamespace(text="retrieved context")
        return RetrievalResult(query=query.query,normalized_query=query.query,retriever="hybrid",chunks=[chunk],citations=[{"document_id":str(uuid.uuid4()),"chunk_id":str(uuid.uuid4()),"score":0.9}],search_statistics={},retrieval_metadata={"retriever":"hybrid"},duration_seconds=0.01)

class ChatServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_conversation_message_token_usage_and_citations(self):
        repo=MemoryRepository();service=ChatService(repo,FakeRetrieval(),MockLLMProvider(),PromptBuilder("system",100),ConversationMemory(10),CitationRenderer());user=uuid.uuid4()
        message,metadata=await service.send_message(repo.conversation.id,user,"What is indexed?",[],{})
        self.assertEqual(message.role,"assistant");self.assertTrue(message.citations);self.assertGreater(message.prompt_tokens,0);self.assertEqual(metadata["retriever"],"hybrid")
    async def test_stream_emits_chunks_and_completion(self):
        repo=MemoryRepository();service=ChatService(repo,FakeRetrieval(),MockLLMProvider(),PromptBuilder("system",100),ConversationMemory(10),CitationRenderer());user=uuid.uuid4()
        events=[x async for x in service.stream_message(repo.conversation.id,user,"What is indexed?",[],{})]
        self.assertEqual(events[-1]["type"],"complete");self.assertTrue(any(x["type"]=="chunk" for x in events))

class ApiRepository:
    async def list_conversations(self,*args): return [],0
    async def list_messages(self,*args): return [],0
    async def delete_conversation(self,*args): return None
class ApiChatService:
    repository=ApiRepository()
    async def create_conversation(self,user,workspace,title,metadata): return SimpleNamespace(id=uuid.uuid4(),title=title,workspace_id=workspace,provider="mock",model="mock-chat-v1",created_at=datetime.now(UTC),updated_at=datetime.now(UTC))
    async def conversation(self,conversation,user): return SimpleNamespace(id=conversation,title="Test",workspace_id=None,provider="mock",model="mock-chat-v1",created_at=datetime.now(UTC),updated_at=datetime.now(UTC))
    async def send_message(self,conversation,user,content,docs,metadata):
        item=SimpleNamespace(id=uuid.uuid4(),conversation_id=conversation,role="assistant",content="Mock response",provider="mock",model="mock-chat-v1",prompt_tokens=3,completion_tokens=2,latency_seconds=0.01,citations=[],metadata_={},created_at=datetime.now(UTC));return item,{}
    async def stream_message(self,*args):
        yield {"type":"chunk","content":"Mock "};yield {"type":"complete","message_id":str(uuid.uuid4()),"citations":[]}
class ApiTests(unittest.TestCase):
    def test_chat_crud_message_and_sse_endpoints(self):
        app=create_app();app.dependency_overrides[get_current_user]=lambda:User(id=uuid.uuid4());app.dependency_overrides[get_chat_service]=ApiChatService
        try:
            with TestClient(app) as client:
                created=client.post("/api/v1/chat/conversations",json={"title":"Test"});cid=created.json()["data"]["id"]
                message=client.post(f"/api/v1/chat/conversations/{cid}/messages",json={"content":"Hi"});stream=client.post(f"/api/v1/chat/conversations/{cid}/stream",json={"content":"Hi"})
            self.assertEqual(created.status_code,201);self.assertEqual(message.json()["data"]["message"]["provider"],"mock");self.assertIn("event: complete",stream.text)
        finally: app.dependency_overrides.clear()
