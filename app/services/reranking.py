from __future__ import annotations

from abc import ABC, abstractmethod

from app.db.repositories.retrieval import RetrievalCandidate


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
        """Return reranked candidates."""


class IdentityReranker(BaseReranker):
    def rerank(self, query: str, candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
        _ = query
        return candidates

