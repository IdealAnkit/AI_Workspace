"""Plain-text parser with conservative encoding handling."""

from pathlib import Path
from uuid import UUID

from app.modules.documents.models.document import Document
from app.modules.document_processing.parsers.base import BaseParser
from app.modules.document_processing.schemas.parsed import ParsedDocument, ParsedPage


class TextParser(BaseParser):
    """Extract UTF text from TXT documents using a safe fallback sequence."""

    name = "txt"

    def supports(self, document: Document) -> bool:
        return document.mime_type == "text/plain" and document.extension == ".txt"

    def extract(self, document_id: UUID, content: bytes, document: Document) -> ParsedDocument:
        warnings: list[str] = []
        text = self._decode(content, warnings)
        return ParsedDocument(
            document_id=document_id,
            title=Path(document.filename).stem,
            page_count=1,
            pages=[ParsedPage(number=1, text=text)],
            text=text,
            metadata=self.metadata(content, document),
            warnings=warnings,
        )

    def metadata(self, content: bytes, document: Document) -> dict:
        return {"format": "txt", "source_size_bytes": len(content)}

    @staticmethod
    def _decode(content: bytes, warnings: list[str]) -> str:
        for encoding in ("utf-8-sig", "utf-16"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        warnings.append("Text was decoded with latin-1 fallback.")
        return content.decode("latin-1")
