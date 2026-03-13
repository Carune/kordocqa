from __future__ import annotations

from html.parser import HTMLParser

from app.services.parsers.base import BaseParser, ParsedBlock, ParsedDocument, ParsingError


class _SimpleHTMLExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._buffer: list[str] = []
        self._active_tag: str | None = None
        self._active_heading_level: int | None = None
        self.heading_stack: list[str] = []
        self.blocks: list[ParsedBlock] = []
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        _ = attrs
        lowered = tag.lower()
        if lowered == "title":
            self._in_title = True
            self._active_tag = "title"
            self._buffer = []
            return

        if lowered in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._active_tag = lowered
            self._active_heading_level = int(lowered[1])
            self._buffer = []
            return

        if lowered in {"p", "li", "div", "section", "article"}:
            self._active_tag = lowered
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "title" and self._in_title:
            title = self._consume_buffer()
            if title:
                self.title = title
            self._in_title = False
            self._active_tag = None
            return

        if lowered in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._active_tag == lowered:
            heading = self._consume_buffer()
            if heading and self._active_heading_level is not None:
                level = self._active_heading_level
                self.heading_stack = self.heading_stack[: max(level - 1, 0)]
                self.heading_stack.append(heading)
            self._active_tag = None
            self._active_heading_level = None
            return

        if lowered == self._active_tag and lowered in {"p", "li", "div", "section", "article"}:
            text = self._consume_buffer()
            if text:
                section_path = " > ".join(self.heading_stack) if self.heading_stack else None
                title = self.heading_stack[-1] if self.heading_stack else None
                self.blocks.append(
                    ParsedBlock(
                        content=text,
                        title=title,
                        section_path=section_path,
                        metadata={"parser_block_tag": lowered},
                    )
                )
            self._active_tag = None

    def handle_data(self, data: str) -> None:
        if self._active_tag is None:
            return
        self._buffer.append(data)

    def _consume_buffer(self) -> str:
        text = " ".join(part.strip() for part in self._buffer if part.strip()).strip()
        self._buffer = []
        return text


class HtmlParser(BaseParser):
    def parse(
        self,
        payload: bytes,
        source_filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        html = payload.decode("utf-8", errors="replace")
        extractor = _SimpleHTMLExtractor()
        extractor.feed(html)
        extractor.close()

        if not extractor.blocks:
            raise ParsingError("HTML document has no extractable text blocks.")

        raw_text = "\n".join(block.content for block in extractor.blocks)

        return ParsedDocument(
            source_filename=source_filename,
            mime_type=mime_type,
            title=extractor.title,
            raw_text=raw_text,
            blocks=extractor.blocks,
            metadata={"parser": "html", "block_count": len(extractor.blocks)},
        )

