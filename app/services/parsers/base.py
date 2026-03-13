from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ParsingError(Exception):
    """Raised when parser cannot extract usable content from a document."""


class UnsupportedFormatError(Exception):
    """Raised when the uploaded file format is not supported."""


@dataclass(slots=True)
class ParsedBlock:
    content: str
    title: str | None = None
    section_path: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    source_filename: str
    mime_type: str | None
    title: str | None
    raw_text: str
    blocks: list[ParsedBlock]
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    @abstractmethod
    def parse(
        self,
        payload: bytes,
        source_filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        """Parse raw bytes and return structured parsed output."""

