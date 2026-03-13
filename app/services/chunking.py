from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.parsers.base import ParsedDocument

_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in normalized.split("\n")]
    normalized = "\n".join(line for line in lines if line)
    normalized = _BLANK_LINES_RE.sub("\n\n", normalized)
    return normalized.strip()


@dataclass(slots=True)
class ChunkDraft:
    content: str
    title: str | None
    section_path: str | None
    page_number: int | None
    metadata: dict[str, Any] = field(default_factory=dict)


class ChunkingService:
    def __init__(self, chunk_size_chars: int = 700, chunk_overlap_chars: int = 80) -> None:
        if chunk_size_chars <= 0:
            raise ValueError("chunk_size_chars must be positive.")
        if chunk_overlap_chars < 0:
            raise ValueError("chunk_overlap_chars cannot be negative.")
        if chunk_overlap_chars >= chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars.")
        self.chunk_size_chars = chunk_size_chars
        self.chunk_overlap_chars = chunk_overlap_chars

    def build_chunks(self, parsed_document: ParsedDocument) -> list[ChunkDraft]:
        chunks: list[ChunkDraft] = []
        for block_index, block in enumerate(parsed_document.blocks):
            normalized_block = normalize_text(block.content)
            if not normalized_block:
                continue

            section_path = block.section_path
            title = block.title or parsed_document.title
            merged_metadata = dict(parsed_document.metadata)
            merged_metadata.update(block.metadata)
            merged_metadata["source_block_index"] = block_index

            for segment in self._split_content(normalized_block):
                chunks.append(
                    ChunkDraft(
                        content=segment,
                        title=title,
                        section_path=section_path,
                        page_number=block.page_number,
                        metadata=dict(merged_metadata),
                    )
                )

        if chunks:
            return chunks

        fallback_text = normalize_text(parsed_document.raw_text)
        if not fallback_text:
            return []

        return [
            ChunkDraft(
                content=fallback_text,
                title=parsed_document.title,
                section_path=None,
                page_number=None,
                metadata=dict(parsed_document.metadata),
            )
        ]

    def _split_content(self, content: str) -> list[str]:
        if len(content) <= self.chunk_size_chars:
            return [content]

        segments: list[str] = []
        start = 0
        min_break_ratio = 0.6

        while start < len(content):
            tentative_end = min(start + self.chunk_size_chars, len(content))
            if tentative_end >= len(content):
                tail = content[start:].strip()
                if tail:
                    segments.append(tail)
                break

            min_break_point = int(start + (self.chunk_size_chars * min_break_ratio))
            split_point = content.rfind(" ", min_break_point, tentative_end)
            if split_point <= start:
                split_point = tentative_end

            piece = content[start:split_point].strip()
            if piece:
                segments.append(piece)

            next_start = max(split_point - self.chunk_overlap_chars, start + 1)
            start = next_start

        return segments

