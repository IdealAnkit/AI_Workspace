"""Composable validation, selection, extraction, normalization, and metadata pipeline."""

import asyncio
import time

from app.core.exceptions import ValidationException
from app.modules.documents.models.document import Document, DocumentStatus
from app.modules.document_processing.extractors.metadata import MetadataExtractor
from app.modules.document_processing.parsers.registry import ParserRegistry
from app.modules.document_processing.processors.normalizer import TextNormalizer
from app.modules.document_processing.schemas.parsed import ParsedDocument, ParsedPage


class DocumentProcessingPipeline:
    """Run independently replaceable processing stages for a stored document."""

    def __init__(
        self,
        parser_registry: ParserRegistry,
        normalizer: TextNormalizer,
        metadata_extractor: MetadataExtractor,
        max_content_bytes: int | None = None,
    ) -> None:
        self.parser_registry = parser_registry
        self.normalizer = normalizer
        self.metadata_extractor = metadata_extractor
        self.max_content_bytes = max_content_bytes

    async def process(self, document: Document, content: bytes) -> ParsedDocument:
        """Validate, parse, normalize, and enrich one provider-neutral byte payload."""
        self._validate(document, content, self.max_content_bytes)
        parser = self.parser_registry.resolve(document)
        started = time.perf_counter()
        parsed = await asyncio.to_thread(parser.extract, document.id, content, document)
        pages = [
            ParsedPage(number=page.number, text=self.normalizer.normalize(page.text))
            for page in parsed.pages
            if self.normalizer.normalize(page.text)
        ]
        text = self.normalizer.normalize("\n\n".join(page.text for page in pages))
        normalized = parsed.model_copy(
            update={
                "pages": pages,
                "page_count": parsed.page_count if parsed.page_count is not None else len(pages) or None,
                "text": text,
            }
        )
        return normalized.model_copy(
            update={
                "metadata": self.metadata_extractor.enrich(normalized),
                "processing_time_seconds": time.perf_counter() - started,
            }
        )

    @staticmethod
    def _validate(document: Document, content: bytes, max_content_bytes: int | None = None) -> None:
        if document.is_deleted:
            raise ValidationException(message="Deleted documents cannot be processed.")
        if document.status not in {
            DocumentStatus.STORED.value,
            DocumentStatus.QUEUED.value,
            DocumentStatus.PROCESSING.value,
        }:
            raise ValidationException(
                message=f"Document cannot be processed while status is {document.status}."
            )
        if not content:
            raise ValidationException(message="Document content is empty.")
        if max_content_bytes is not None and len(content) > max_content_bytes:
            raise ValidationException(message="Document content exceeds the configured processing limit.")
