"""Composable chunk-to-vector indexing pipeline."""

import hashlib

from app.modules.document_processing.models.processing import ProcessedDocument
from app.modules.indexing.chunkers import BaseChunker, ChunkDraft
from app.modules.indexing.models import DocumentChunk


class IndexingPipeline:
    def __init__(self, chunkers: list[BaseChunker], default_chunk_size: int, default_overlap: int) -> None:
        self.chunkers = chunkers
        self.default_chunk_size = default_chunk_size
        self.default_overlap = default_overlap

    def chunk(self, document: ProcessedDocument, *, version: int, embedding_job_id, index_metadata_id) -> list[DocumentChunk]:
        chunker = next((item for item in self.chunkers if item.supports(document)), None)
        if chunker is None:
            raise ValueError("No chunker supports this processed document.")
        metadata = chunker.metadata(document)
        drafts = chunker.split(document, self.default_chunk_size, self.default_overlap)
        return [self._to_model(document, draft, position, version, embedding_job_id, index_metadata_id, metadata) for position, draft in enumerate(drafts)]

    @staticmethod
    def _to_model(document: ProcessedDocument, draft: ChunkDraft, position: int, version: int, embedding_job_id, index_metadata_id, chunker_metadata: dict) -> DocumentChunk:
        text = draft.text.strip()
        return DocumentChunk(
            document_id=document.document_id,
            processing_job_id=document.processing_job_id,
            embedding_job_id=embedding_job_id,
            index_metadata_id=index_metadata_id,
            chunk_index=position,
            text=text,
            token_count=len(text.split()),
            character_count=len(text),
            page_start=draft.page_start,
            page_end=draft.page_end,
            section_title=draft.section_title,
            heading_path=draft.heading_path,
            language=document.language,
            metadata_={**chunker_metadata, **draft.metadata},
            checksum=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            version=version,
        )
