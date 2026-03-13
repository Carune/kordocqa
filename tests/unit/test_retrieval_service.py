from __future__ import annotations

import uuid

from app.db.repositories.retrieval import RetrievalCandidate
from app.services.embeddings import EmbeddingProviderUnavailableError
from app.services.retrieval import RetrievalService


class FakeRepository:
    def __init__(
        self,
        *,
        lexical_candidates: list[RetrievalCandidate] | None = None,
        semantic_candidates: list[RetrievalCandidate] | None = None,
    ) -> None:
        self.lexical_candidates = lexical_candidates or []
        self.semantic_candidates = semantic_candidates or []
        self.updated_embeddings: list[tuple[uuid.UUID, list[float]]] = []
        self.ensure_content_tsv_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self._unembedded_rows: list[tuple[uuid.UUID, str]] = []

    def ensure_content_tsv(self, document_id: uuid.UUID | None = None) -> int:
        _ = document_id
        self.ensure_content_tsv_calls += 1
        return 0

    def lexical_search(
        self,
        *,
        query: str,
        limit: int,
        document_id: uuid.UUID | None = None,
        trigram_threshold: float = 0.2,
    ) -> list[RetrievalCandidate]:
        _ = query
        _ = limit
        _ = document_id
        _ = trigram_threshold
        return self.lexical_candidates

    def semantic_search(
        self,
        *,
        query_embedding: list[float],
        limit: int,
        document_id: uuid.UUID | None = None,
    ) -> list[RetrievalCandidate]:
        _ = query_embedding
        _ = limit
        _ = document_id
        return self.semantic_candidates

    def list_chunks_without_embedding(
        self,
        *,
        limit: int,
        document_id: uuid.UUID | None = None,
    ) -> list[tuple[uuid.UUID, str]]:
        _ = document_id
        rows = self._unembedded_rows[:limit]
        self._unembedded_rows = self._unembedded_rows[limit:]
        return rows

    def update_chunk_embedding(self, *, chunk_id: uuid.UUID, embedding: list[float]) -> None:
        self.updated_embeddings.append((chunk_id, embedding))

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class FixedEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class UnconfiguredProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        _ = texts
        raise EmbeddingProviderUnavailableError("not configured")


def _candidate(
    chunk_id: uuid.UUID,
    lexical: float | None,
    semantic: float | None,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        content=f"chunk-{chunk_id}",
        title=None,
        section_path=None,
        page_number=None,
        metadata=None,
        lexical_score=lexical,
        semantic_score=semantic,
    )


def test_retrieval_service_returns_hybrid_results_with_rrf() -> None:
    chunk_a = uuid.uuid4()
    chunk_b = uuid.uuid4()
    chunk_c = uuid.uuid4()

    repository = FakeRepository(
        lexical_candidates=[
            _candidate(chunk_a, lexical=0.9, semantic=None),
            _candidate(chunk_b, lexical=0.8, semantic=None),
        ],
        semantic_candidates=[
            _candidate(chunk_b, lexical=None, semantic=0.95),
            _candidate(chunk_c, lexical=None, semantic=0.7),
        ],
    )

    service = RetrievalService(
        repository=repository,
        embedding_provider=FixedEmbeddingProvider(),  # type: ignore[arg-type]
        trigram_threshold=0.2,
        auto_index_max_chunks=10,
    )
    result = service.retrieve(query="policy", top_k=3, lexical_k=5, semantic_k=5)

    assert result.status == "ok"
    assert result.retrieval_mode == "hybrid"
    assert len(result.chunks) == 3
    assert result.chunks[0].chunk_id == chunk_b


def test_retrieval_service_falls_back_to_lexical_when_provider_unconfigured() -> None:
    chunk_a = uuid.uuid4()
    repository = FakeRepository(
        lexical_candidates=[_candidate(chunk_a, lexical=0.9, semantic=None)],
        semantic_candidates=[],
    )
    service = RetrievalService(
        repository=repository,
        embedding_provider=UnconfiguredProvider(),  # type: ignore[arg-type]
        auto_index_max_chunks=10,
    )

    result = service.retrieve(query="policy", top_k=3, lexical_k=5, semantic_k=5)

    assert result.status == "ok"
    assert result.retrieval_mode == "lexical_only"
    assert len(result.chunks) == 1
    assert result.chunks[0].chunk_id == chunk_a


def test_retrieval_service_indexes_missing_embeddings_in_batches() -> None:
    repository = FakeRepository()
    chunk_a = uuid.uuid4()
    chunk_b = uuid.uuid4()
    repository._unembedded_rows = [(chunk_a, "A"), (chunk_b, "B")]

    service = RetrievalService(
        repository=repository,
        embedding_provider=FixedEmbeddingProvider(),  # type: ignore[arg-type]
        index_batch_size=1,
        auto_index_max_chunks=10,
    )
    indexed = service.index_missing_embeddings()

    assert indexed == 2
    assert len(repository.updated_embeddings) == 2
    assert repository.commit_calls == 2
