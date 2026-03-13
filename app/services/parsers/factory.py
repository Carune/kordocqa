from __future__ import annotations

from pathlib import Path

from app.services.parsers.base import BaseParser, ParsedDocument, UnsupportedFormatError
from app.services.parsers.docx_parser import DocxParser
from app.services.parsers.html_parser import HtmlParser
from app.services.parsers.pdf_parser import PdfParser
from app.services.parsers.txt_parser import TxtParser


class ParserFactory:
    def __init__(self) -> None:
        self._extension_parsers: dict[str, BaseParser] = {
            ".pdf": PdfParser(),
            ".docx": DocxParser(),
            ".txt": TxtParser(),
            ".html": HtmlParser(),
            ".htm": HtmlParser(),
        }
        self._mime_parsers: dict[str, BaseParser] = {
            "application/pdf": self._extension_parsers[".pdf"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
                self._extension_parsers[".docx"]
            ),
            "text/plain": self._extension_parsers[".txt"],
            "text/html": self._extension_parsers[".html"],
        }

    def parse_document(
        self,
        payload: bytes,
        source_filename: str,
        mime_type: str | None,
    ) -> ParsedDocument:
        parser = self._select_parser(source_filename=source_filename, mime_type=mime_type)
        return parser.parse(payload=payload, source_filename=source_filename, mime_type=mime_type)

    def _select_parser(self, source_filename: str, mime_type: str | None) -> BaseParser:
        extension = Path(source_filename).suffix.lower()
        if extension in self._extension_parsers:
            return self._extension_parsers[extension]

        normalized_mime = (mime_type or "").split(";", maxsplit=1)[0].strip().lower()
        if normalized_mime in self._mime_parsers:
            return self._mime_parsers[normalized_mime]

        raise UnsupportedFormatError(f"Unsupported file format: {source_filename} ({mime_type})")

