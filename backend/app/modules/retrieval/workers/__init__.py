"""No background workers are used by the synchronous retrieval engine."""

from app.modules.retrieval.workers.base import RetrievalWorker

__all__ = ["RetrievalWorker"]
