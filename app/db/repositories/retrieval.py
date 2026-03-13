from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(slots=True)
class RetrievalCandidate:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    title: str | None
    section_path: str | None
    page_number: int | None
    metadata: dict[str, Any] | None
    lexical_score: float | None = None
    semantic_score: float | None = None
    fusion_score: float | None = None


class RetrievalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_content_tsv(self, document_id: uuid.UUID | None = None) -> int:
        stmt = text(
            """
            UPDATE document_chunks
            SET content_tsv = to_tsvector(
                'simple',
                concat_ws(' ', coalesce(title, ''), coalesce(section_path, ''), content)
            )
            WHERE (:document_id IS NULL OR document_id = :document_id)
              AND content_tsv IS NULL
            """
        )
        result = self.db.execute(stmt, {"document_id": document_id})
        self.db.commit()
        return result.rowcount or 0

    def list_chunks_without_embedding(
        self,
        *,
        limit: int,
        document_id: uuid.UUID | None = None,
    ) -> list[tuple[uuid.UUID, str]]:
        stmt = text(
            """
            SELECT id, content
            FROM document_chunks
            WHERE embedding IS NULL
              AND (:document_id IS NULL OR document_id = :document_id)
            ORDER BY created_at ASC
            LIMIT :limit
            """
        )
        rows = self.db.execute(stmt, {"limit": limit, "document_id": document_id}).mappings().all()
        return [(row["id"], row["content"]) for row in rows]

    def update_chunk_embedding(self, *, chunk_id: uuid.UUID, embedding: list[float]) -> None:
        vector_literal = self._vector_literal(embedding)
        stmt = text(
            f"""
            UPDATE document_chunks
            SET embedding = '{vector_literal}'::vector
            WHERE id = :chunk_id
            """
        )
        self.db.execute(stmt, {"chunk_id": chunk_id})

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def semantic_search(
        self,
        *,
        query_embedding: list[float],
        limit: int,
        document_id: uuid.UUID | None = None,
    ) -> list[RetrievalCandidate]:
        if not query_embedding:
            return []

        vector_literal = self._vector_literal(query_embedding)
        stmt = text(
            f"""
            SELECT
                id AS chunk_id,
                document_id,
                content,
                title,
                section_path,
                page_number,
                metadata,
                (1 - (embedding <=> '{vector_literal}'::vector)) AS semantic_score
            FROM document_chunks
            WHERE embedding IS NOT NULL
              AND (:document_id IS NULL OR document_id = :document_id)
            ORDER BY embedding <=> '{vector_literal}'::vector
            LIMIT :limit
            """
        )
        rows = self.db.execute(stmt, {"limit": limit, "document_id": document_id}).mappings().all()
        return [
            self._candidate_from_row(row=row, semantic_score=row["semantic_score"])
            for row in rows
        ]

    def lexical_search(
        self,
        *,
        query: str,
        limit: int,
        document_id: uuid.UUID | None = None,
        trigram_threshold: float = 0.2,
    ) -> list[RetrievalCandidate]:
        stmt = text(
            """
            WITH query_data AS (
                SELECT plainto_tsquery('simple', :query) AS tsq
            )
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                dc.content,
                dc.title,
                dc.section_path,
                dc.page_number,
                dc.metadata,
                ts_rank_cd(
                    coalesce(
                        dc.content_tsv,
                        to_tsvector(
                            'simple',
                            concat_ws(
                                ' ',
                                coalesce(dc.title, ''),
                                coalesce(dc.section_path, ''),
                                dc.content
                            )
                        )
                    ),
                    query_data.tsq
                ) AS lexical_score,
                similarity(dc.content, :query) AS trigram_score
            FROM document_chunks dc, query_data
            WHERE (:document_id IS NULL OR dc.document_id = :document_id)
              AND (
                coalesce(
                    dc.content_tsv,
                    to_tsvector(
                        'simple',
                        concat_ws(
                            ' ',
                            coalesce(dc.title, ''),
                            coalesce(dc.section_path, ''),
                            dc.content
                        )
                    )
                ) @@ query_data.tsq
                OR similarity(dc.content, :query) >= :trigram_threshold
              )
            ORDER BY GREATEST(
                ts_rank_cd(
                    coalesce(
                        dc.content_tsv,
                        to_tsvector(
                            'simple',
                            concat_ws(
                                ' ',
                                coalesce(dc.title, ''),
                                coalesce(dc.section_path, ''),
                                dc.content
                            )
                        )
                    ),
                    query_data.tsq
                ),
                similarity(dc.content, :query)
            ) DESC
            LIMIT :limit
            """
        )
        rows = self.db.execute(
            stmt,
            {
                "query": query,
                "limit": limit,
                "document_id": document_id,
                "trigram_threshold": trigram_threshold,
            },
        ).mappings().all()
        return [
            self._candidate_from_row(row=row, lexical_score=row["lexical_score"])
            for row in rows
        ]

    def _candidate_from_row(
        self,
        *,
        row: dict[str, Any],
        lexical_score: float | None = None,
        semantic_score: float | None = None,
    ) -> RetrievalCandidate:
        return RetrievalCandidate(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            content=row["content"],
            title=row["title"],
            section_path=row["section_path"],
            page_number=row["page_number"],
            metadata=row["metadata"],
            lexical_score=self._safe_float(lexical_score),
            semantic_score=self._safe_float(semantic_score),
        )

    def _vector_literal(self, embedding: list[float]) -> str:
        return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"

    def _safe_float(self, value: float | int | None) -> float | None:
        if value is None:
            return None
        return float(value)
