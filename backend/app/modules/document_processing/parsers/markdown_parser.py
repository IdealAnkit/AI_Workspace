"""Markdown parser backed by markdown-it-py for format-aware metadata."""

from pathlib import Path
from uuid import UUID

from markdown_it import MarkdownIt

from app.modules.documents.models.document import Document
from app.modules.document_processing.parsers.base import BaseParser
from app.modules.document_processing.schemas.parsed import ParsedDocument, ParsedPage


class MarkdownParser(BaseParser):
    """Extract Markdown source text and title while retaining document semantics."""

    name = "markdown"

    def __init__(self) -> None:
        self.markdown = MarkdownIt()

    def supports(self, document: Document) -> bool:
        return document.extension in {".md", ".markdown"} and document.mime_type in {
            "text/markdown",
            "text/x-markdown",
            "text/plain",
        }

    def extract(self, document_id: UUID, content: bytes, document: Document) -> ParsedDocument:
        text = content.decode("utf-8-sig", errors="replace")
        tokens = self.markdown.parse(text)
        title = self._first_heading(tokens) or Path(document.filename).stem
        return ParsedDocument(
            document_id=document_id,
            title=title,
            page_count=1,
            pages=[ParsedPage(number=1, text=text)],
            text=text,
            metadata=self.metadata(content, document),
            warnings=[],
        )

    def metadata(self, content: bytes, document: Document) -> dict:
        return {"format": "markdown", "source_size_bytes": len(content)}

    @staticmethod
    def _first_heading(tokens: list) -> str | None:
        for index, token in enumerate(tokens[:-1]):
            if token.type == "heading_open" and tokens[index + 1].type == "inline":
                return tokens[index + 1].content.strip() or None
        return None
