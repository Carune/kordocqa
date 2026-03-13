from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.db.repositories.retrieval import RetrievalCandidate, RetrievalRepository
from app.services.embeddings import (
    BaseEmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
)
from app.services.reranking import BaseReranker, IdentityReranker


@dataclass(slots=True)
class RetrievalResult:
    status: str
    retrieval_mode: str
    chunks: list[RetrievalCandidate]


class RetrievalService:
    def __init__(
        self,
        *,
        repository: RetrievalRepository,
        embedding_provider: BaseEmbeddingProvider,
        reranker: BaseReranker | None = None,
        trigram_threshold: float = 0.2,
        index_batch_size: int = 32,
        auto_index_max_chunks: int = 500,
        rrf_k: int = 60,
    ) -> None:
        self.repository = repository
        self.embedding_provider = embedding_provider
        self.reranker = reranker or IdentityReranker()
        self.trigram_threshold = trigram_threshold
        self.index_batch_size = index_batch_size
        self.auto_index_max_chunks = auto_index_max_chunks
        self.rrf_k = rrf_k

    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        lexical_k: int,
        semantic_k: int,
        document_id: uuid.UUID | None = None,
    ) -> RetrievalResult:
        cleaned_query = query.strip()
        if not cleaned_query:
            return RetrievalResult(status="degraded", retrieval_mode="lexical_only", chunks=[])

        self.repository.ensure_content_tsv(document_id=document_id)
        lexical_candidates = self.repository.lexical_search(
            query=cleaned_query,
            limit=lexical_k,
            document_id=document_id,
            trigram_threshold=self.trigram_threshold,
        )

        semantic_candidates: list[RetrievalCandidate] = []
        retrieval_mode = "lexical_only"

        try:
            self.index_missing_embeddings(document_id=document_id)
            query_embedding = self.embedding_provider.embed_texts([cleaned_query])[0]
            semantic_candidates = self.repository.semantic_search(
                query_embedding=query_embedding,
                limit=semantic_k,
                document_id=document_id,
            )
            if semantic_candidates:
                retrieval_mode = "hybrid"
        except EmbeddingProviderUnavailableError:
            retrieval_mode = "lexical_only"
        except EmbeddingProviderError:
            retrieval_mode = "lexical_only"

        fused_candidates = self._rrf_fuse(
            lexical_candidates=lexical_candidates,
            semantic_candidates=semantic_candidates,
        )
        reranked = self.reranker.rerank(cleaned_query, fused_candidates)[:top_k]

        if not reranked:
            return RetrievalResult(status="degraded", retrieval_mode=retrieval_mode, chunks=[])
        return RetrievalResult(status="ok", retrieval_mode=retrieval_mode, chunks=reranked)

    def index_missing_embeddings(self, *, document_id: uuid.UUID | None = None) -> int:
        indexed = 0
        remaining = self.auto_index_max_chunks

        while remaining > 0:
            batch_limit = min(self.index_batch_size, remaining)
            rows = self.repository.list_chunks_without_embedding(
                limit=batch_limit,
                document_id=document_id,
            )
            if not rows:
                break

            chunk_ids = [chunk_id for chunk_id, _ in rows]
            contents = [content for _, content in rows]
            try:
                embeddings = self.embedding_provider.embed_texts(contents)
            except EmbeddingProviderUnavailableError:
                return indexed
            except EmbeddingProviderError:
                self.repository.rollback()
                raise

            if len(embeddings) != len(chunk_ids):
                self.repository.rollback()
                raise EmbeddingProviderError("Embedding provider returned mismatched vector count.")

            for chunk_id, embedding in zip(chunk_ids, embeddings, strict=True):
                self.repository.update_chunk_embedding(chunk_id=chunk_id, embedding=embedding)
                indexed += 1
                remaining -= 1

            self.repository.commit()
        return indexed

    def _rrf_fuse(
        self,
        *,
        lexical_candidates: list[RetrievalCandidate],
        semantic_candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        aggregated: dict[uuid.UUID, tuple[float, RetrievalCandidate]] = {}

        for rank, candidate in enumerate(lexical_candidates, start=1):
            score = 1.0 / (self.rrf_k + rank)
            previous = aggregated.get(candidate.chunk_id)
            if previous is None:
                aggregated[candidate.chunk_id] = (score, candidate)
            else:
                total, existing = previous
                existing.lexical_score = candidate.lexical_score
                aggregated[candidate.chunk_id] = (total + score, existing)

        for rank, candidate in enumerate(semantic_candidates, start=1):
            score = 1.0 / (self.rrf_k + rank)
            previous = aggregated.get(candidate.chunk_id)
            if previous is None:
                aggregated[candidate.chunk_id] = (score, candidate)
            else:
                total, existing = previous
                existing.semantic_score = candidate.semantic_score
                aggregated[candidate.chunk_id] = (total + score, existing)

        ranked = sorted(
            aggregated.values(),
            key=lambda item: (
                item[0],
                item[1].semantic_score or 0.0,
                item[1].lexical_score or 0.0,
            ),
            reverse=True,
        )
        output: list[RetrievalCandidate] = []
        for fusion_score, candidate in ranked:
            candidate.fusion_score = fusion_score
            output.append(candidate)
        return output
