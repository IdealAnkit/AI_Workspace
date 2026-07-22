from typing import Any

from app.modules.retrieval.retrievers.types import RetrievedChunk


class CitationBuilder:
    def build(self, chunk: RetrievedChunk) -> dict[str, Any]:
        return {"document_id": chunk.document_id, "document_title": chunk.metadata.get("document_title"), "chunk_id": chunk.id, "chunk_index": chunk.chunk_index, "page_number": chunk.page_start, "section_title": chunk.section_title, "score": chunk.score, "metadata": chunk.metadata}
