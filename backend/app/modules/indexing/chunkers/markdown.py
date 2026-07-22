"""Markdown-aware chunking which preserves heading context."""

import re

from app.modules.document_processing.models.processing import ProcessedDocument
from app.modules.indexing.chunkers.base import BaseChunker, ChunkDraft
from app.modules.indexing.chunkers.fixed_size import FixedSizeChunker


class MarkdownChunker(BaseChunker):
    name = "markdown"
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

    def supports(self, document: ProcessedDocument) -> bool:
        return document.metadata_.get("format") == "markdown" or document.metadata_.get("source_format") == "markdown"

    def split(self, document: ProcessedDocument, chunk_size: int, overlap: int) -> list[ChunkDraft]:
        matches = list(self.heading_pattern.finditer(document.text))
        if not matches:
            return FixedSizeChunker().split(document, chunk_size, overlap)
        drafts: list[ChunkDraft] = []
        path: list[str] = []
        for position, match in enumerate(matches):
            level, title = len(match.group(1)), match.group(2).strip()
            path = path[: level - 1] + [title]
            end = matches[position + 1].start() if position + 1 < len(matches) else len(document.text)
            section = document.text[match.end() : end].strip()
            if not section:
                continue
            temporary = ProcessedDocument(text=section, pages=[], metadata_={}, warnings=[])
            for item in FixedSizeChunker().split(temporary, chunk_size, overlap):
                drafts.append(ChunkDraft(text=item.text, section_title=title, heading_path=list(path)))
        return drafts

    def metadata(self, document: ProcessedDocument) -> dict:
        return {"chunker": self.name, "heading_aware": True}
