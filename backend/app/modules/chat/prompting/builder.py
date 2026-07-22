from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Prompt:
    text: str; prompt_tokens: int; metadata: dict[str, Any]
class PromptBuilder:
    def __init__(self, system_prompt: str, max_tokens: int) -> None: self.system_prompt, self.max_tokens = system_prompt, max_tokens
    def build(self, history, context, question: str) -> Prompt:
        parts = [f"System:\n{self.system_prompt}"]
        for message in history: parts.append(f"{message.role}: {message.content}")
        for index, item in enumerate(context, 1): parts.append(f"[Context {index}] {item.text}")
        parts.append(f"User question:\n{question}")
        selected: list[str] = []
        for part in reversed(parts):
            if len((part + "\n" + "\n".join(selected)).split()) > self.max_tokens: continue
            selected.insert(0, part)
        text = "\n\n".join(selected)
        return Prompt(text, len(text.split()), {"history_messages": len(history), "context_blocks": len(context)})
