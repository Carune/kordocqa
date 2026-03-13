from __future__ import annotations

from app.services.parsers.base import BaseParser, ParsedBlock, ParsedDocument, ParsingError


class TxtParser(BaseParser):
    _ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp949", "euc-kr")

    def parse(
        self,
        payload: bytes,
        source_filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        text = self._decode_text(payload).strip()
        if not text:
            raise ParsingError("TXT document is empty after decoding.")

        return ParsedDocument(
            source_filename=source_filename,
            mime_type=mime_type,
            title=None,
            raw_text=text,
            blocks=[ParsedBlock(content=text)],
            metadata={"parser": "txt"},
        )

    def _decode_text(self, payload: bytes) -> str:
        for encoding in self._ENCODINGS:
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        return payload.decode("utf-8", errors="replace")

