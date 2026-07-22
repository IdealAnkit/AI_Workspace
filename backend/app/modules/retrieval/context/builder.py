"""Citation-preserving context preparation without generating answers."""

from app.modules.retrieval.retrievers.types import RetrievedChunk


class ContextBuilder:
    def __init__(self, max_tokens: int) -> None: self.max_tokens = max_tokens
    def build(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        unique: list[RetrievedChunk] = []
        seen: set[str] = set()
        remaining = self.max_tokens
        for chunk in chunks:
            key = chunk.checksum or chunk.text.strip().lower()
            if key in seen: continue
            tokens = len(chunk.text.split())
            if tokens > remaining: continue
            seen.add(key); unique.append(chunk); remaining -= tokens
        return self._merge_adjacent(unique)
    @staticmethod
    def _merge_adjacent(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        merged: list[RetrievedChunk] = []
        for chunk in chunks:
            if merged and merged[-1].document_id == chunk.document_id and merged[-1].chunk_index + 1 == chunk.chunk_index:
                previous = merged[-1]
                previous.text = f"{previous.text}\n\n{chunk.text}"
                previous.page_end = chunk.page_end or previous.page_end
                previous.score = max(previous.score, chunk.score)
                previous.ranking_metadata["merged_chunk_ids"] = previous.ranking_metadata.get("merged_chunk_ids", []) + [str(chunk.id)]
            else: merged.append(chunk)
        return merged
