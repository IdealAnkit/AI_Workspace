class ConversationMemory:
    def __init__(self, max_messages: int) -> None: self.max_messages = max_messages
    def recent(self, messages): return messages[-self.max_messages:] if self.max_messages else []
