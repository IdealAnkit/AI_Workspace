"""PDF parser powered by pdfplumber."""

import io
from pathlib import Path
from uuid import UUID

import pdfplumber

from app.modules.documents.models.document import Document
from app.modules.document_processing.parsers.base import BaseParser
from app.modules.document_processing.schemas.parsed import ParsedDocument, ParsedPage


class PdfParser(BaseParser):
    """Extract page text and available PDF metadata without OCR."""

    name = "pdf"

    def supports(self, document: Document) -> bool:
        return document.mime_type == "application/pdf" and document.extension == ".pdf"

    def extract(self, document_id: UUID, content: bytes, document: Document) -> ParsedDocument:
        warnings: list[str] = []
        pages: list[ParsedPage] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            raw_metadata = dict(pdf.metadata or {})
            for number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    warnings.append(f"Page {number} contains no extractable text.")
                pages.append(ParsedPage(number=number, text=text))
        text = "\n\n".join(page.text for page in pages if page.text.strip())
        title = raw_metadata.get("Title") or Path(document.filename).stem
        metadata = self.metadata(content, document)
        metadata["pdf"] = raw_metadata
        metadata["producer"] = raw_metadata.get("Producer")
        return ParsedDocument(
            document_id=document_id,
            title=str(title) if title else None,
            page_count=len(pages),
            pages=pages,
            text=text,
            metadata=metadata,
            warnings=warnings,
        )

    def metadata(self, content: bytes, document: Document) -> dict:
        return {"format": "pdf", "source_size_bytes": len(content)}
