from collections.abc import AsyncIterator
from app.modules.chat.providers.base import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    def __init__(self, model: str = "mock-chat-v1", max_tokens: int = 8192) -> None: self._model, self._max = model, max_tokens
    async def generate(self, prompt: str) -> str:
        question = prompt.rsplit("User question:", 1)[-1].strip().splitlines()[0]
        contexts = prompt.count("[Context")
        return f"Mock response using {contexts} retrieved context block(s): {question}"
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        for word in (await self.generate(prompt)).split(" "):
            yield word + " "
    def model_name(self) -> str: return self._model
    def provider_name(self) -> str: return "mock"
    def max_context_tokens(self) -> int: return self._max
    def supports_streaming(self) -> bool: return True
