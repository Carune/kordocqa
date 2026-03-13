from __future__ import annotations

from io import BytesIO

from app.services.parsers.base import BaseParser, ParsedBlock, ParsedDocument, ParsingError


class PdfParser(BaseParser):
    def parse(
        self,
        payload: bytes,
        source_filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise ParsingError("pypdf dependency is required for PDF parsing.") from exc

        try:
            reader = PdfReader(BytesIO(payload))
        except Exception as exc:  # noqa: BLE001
            raise ParsingError("Invalid PDF file.") from exc

        blocks: list[ParsedBlock] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            blocks.append(
                ParsedBlock(
                    content=text,
                    page_number=page_number,
                    metadata={"parser_page_number": page_number},
                )
            )

        if not blocks:
            raise ParsingError("PDF document has no extractable text.")

        title = None
        if reader.metadata is not None:
            title = reader.metadata.title

        raw_text = "\n".join(block.content for block in blocks)
        return ParsedDocument(
            source_filename=source_filename,
            mime_type=mime_type,
            title=title,
            raw_text=raw_text,
            blocks=blocks,
            metadata={"parser": "pdf", "page_count": len(reader.pages)},
        )

