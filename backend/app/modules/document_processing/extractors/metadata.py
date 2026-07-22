"""Format-independent metadata extracted after text normalization."""

from typing import Any

from app.modules.document_processing.schemas.parsed import ParsedDocument


class MetadataExtractor:
    """Add standard, parser-independent text metrics to structured content."""

    def enrich(self, parsed: ParsedDocument) -> dict[str, Any]:
        metadata = dict(parsed.metadata)
        metadata["word_count"] = len(parsed.text.split())
        metadata["character_count"] = len(parsed.text)
        metadata["page_count"] = parsed.page_count
        return metadata
