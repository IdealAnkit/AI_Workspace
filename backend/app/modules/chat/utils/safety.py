from abc import ABC, abstractmethod
class InputValidator(ABC):
    @abstractmethod
    def validate(self, content: str) -> None: ...
class OutputValidator(ABC):
    @abstractmethod
    def validate(self, content: str) -> None: ...
class PromptInjectionDetector(ABC): pass
class ContentFilter(ABC): pass
class NoOpValidator(InputValidator, OutputValidator):
    def validate(self, content: str) -> None: return None
