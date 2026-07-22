"""Extensible parser registry; pipeline selection is never hardcoded."""

from app.core.exceptions import ValidationException
from app.modules.documents.models.document import Document
from app.modules.document_processing.parsers.base import BaseParser


class ParserRegistry:
    """Resolve one parser from registered implementations."""

    def __init__(self, parsers: list[BaseParser] | None = None) -> None:
        self._parsers = parsers or []

    def register(self, parser: BaseParser) -> None:
        self._parsers.append(parser)

    def resolve(self, document: Document) -> BaseParser:
        for parser in self._parsers:
            if parser.supports(document):
                return parser
        raise ValidationException(message=f"No parser is registered for {document.mime_type}.")

    @property
    def parser_names(self) -> list[str]:
        return [parser.name for parser in self._parsers]
