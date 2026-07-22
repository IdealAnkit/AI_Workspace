"""Recursive separator-aware text chunker."""

from app.modules.document_processing.models.processing import ProcessedDocument
from app.modules.indexing.chunkers.base import BaseChunker, ChunkDraft
from app.modules.indexing.chunkers.fixed_size import FixedSizeChunker


class RecursiveChunker(BaseChunker):
    name = "recursive"
    separators = ("\n\n", "\n", ". ", " ")

    def supports(self, document: ProcessedDocument) -> bool:
        return bool(document.text)

    def split(self, document: ProcessedDocument, chunk_size: int, overlap: int) -> list[ChunkDraft]:
        if not document.text.strip():
            return []
        parts = self._split(document.text.strip(), chunk_size)
        if not parts:
            return FixedSizeChunker().split(document, chunk_size, overlap)
        drafts: list[ChunkDraft] = []
        trailing = ""
        for part in parts:
            value = f"{trailing}{part}".strip()
            if value:
                drafts.append(ChunkDraft(text=value))
            trailing = value[-overlap:] if overlap else ""
        return drafts

    def metadata(self, document: ProcessedDocument) -> dict:
        return {"chunker": self.name, "separators": list(self.separators)}

    def _split(self, text: str, chunk_size: int) -> list[str]:
        if len(text) <= chunk_size:
            return [text]
        for separator in self.separators:
            pieces = text.split(separator)
            if len(pieces) == 1:
                continue
            results: list[str] = []
            current = ""
            for piece in pieces:
                candidate = f"{current}{separator if current else ''}{piece}"
                if len(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current:
                        results.append(current)
                    if len(piece) > chunk_size:
                        results.extend(self._split(piece, chunk_size))
                        current = ""
                    else:
                        current = piece
            if current:
                results.append(current)
            return results
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]
