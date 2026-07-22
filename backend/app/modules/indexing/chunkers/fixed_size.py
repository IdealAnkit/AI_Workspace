"""Deterministic fixed-size chunker."""

from app.modules.document_processing.models.processing import ProcessedDocument
from app.modules.indexing.chunkers.base import BaseChunker, ChunkDraft


class FixedSizeChunker(BaseChunker):
    name = "fixed_size"

    def supports(self, document: ProcessedDocument) -> bool:
        return bool(document.text)

    def split(self, document: ProcessedDocument, chunk_size: int, overlap: int) -> list[ChunkDraft]:
        if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("Chunk overlap must be non-negative and smaller than the chunk size.")
        text = document.text.strip()
        if not text:
            return []
        drafts: list[ChunkDraft] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            if end < len(text):
                boundary = text.rfind(" ", start, end)
                if boundary > start:
                    end = boundary
            value = text[start:end].strip()
            if value:
                drafts.append(ChunkDraft(text=value, **self._page_metadata(document, start, end)))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
        return drafts

    def metadata(self, document: ProcessedDocument) -> dict:
        return {"chunker": self.name, "source_pages": document.page_count or 0}

    @staticmethod
    def _page_metadata(document: ProcessedDocument, start: int, end: int) -> dict:
        offset = 0
        pages = document.pages or []
        page_start = page_end = None
        for page in pages:
            page_text = str(page.get("text", ""))
            page_number = page.get("number")
            page_end_offset = offset + len(page_text)
            if page_number and page_start is None and start <= page_end_offset:
                page_start = int(page_number)
            if page_number and end <= page_end_offset:
                page_end = int(page_number)
                break
            offset = page_end_offset + 2
        return {"page_start": page_start, "page_end": page_end}
