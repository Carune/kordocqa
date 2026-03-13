from __future__ import annotations

from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from app.services.parsers.base import (
    BaseParser,
    ParsedBlock,
    ParsedDocument,
    ParsingError,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DC_NS = "http://purl.org/dc/elements/1.1/"
XML_NS = {"w": W_NS, "dc": DC_NS}


class DocxParser(BaseParser):
    def parse(
        self,
        payload: bytes,
        source_filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        try:
            archive = ZipFile(BytesIO(payload))
        except BadZipFile as exc:
            raise ParsingError("Invalid DOCX file.") from exc

        try:
            document_xml = archive.read("word/document.xml")
        except KeyError as exc:
            raise ParsingError("DOCX missing word/document.xml.") from exc

        title = self._extract_title(archive)
        root = ElementTree.fromstring(document_xml)
        blocks: list[ParsedBlock] = []
        heading_stack: list[str] = []

        for paragraph in root.findall(".//w:p", XML_NS):
            text_parts = [node.text for node in paragraph.findall(".//w:t", XML_NS) if node.text]
            text = "".join(text_parts).strip()
            if not text:
                continue

            style = self._paragraph_style(paragraph)
            heading_level = self._heading_level(style)
            if heading_level is not None:
                heading_stack = heading_stack[: max(heading_level - 1, 0)]
                heading_stack.append(text)
                continue

            section_path = " > ".join(heading_stack) if heading_stack else None
            block_title = heading_stack[-1] if heading_stack else title

            blocks.append(
                ParsedBlock(
                    content=text,
                    title=block_title,
                    section_path=section_path,
                    metadata={"parser_style": style},
                )
            )

        if not blocks:
            raise ParsingError("DOCX document has no extractable paragraphs.")

        raw_text = "\n".join(block.content for block in blocks)
        return ParsedDocument(
            source_filename=source_filename,
            mime_type=mime_type,
            title=title,
            raw_text=raw_text,
            blocks=blocks,
            metadata={"parser": "docx", "block_count": len(blocks)},
        )

    def _extract_title(self, archive: ZipFile) -> str | None:
        try:
            core_xml = archive.read("docProps/core.xml")
        except KeyError:
            return None
        try:
            root = ElementTree.fromstring(core_xml)
        except ElementTree.ParseError:
            return None
        title = root.find(".//dc:title", XML_NS)
        if title is None or title.text is None:
            return None
        value = title.text.strip()
        return value or None

    def _paragraph_style(self, paragraph: ElementTree.Element) -> str | None:
        style = paragraph.find(".//w:pStyle", XML_NS)
        if style is None:
            return None
        return style.attrib.get(f"{{{W_NS}}}val")

    def _heading_level(self, style: str | None) -> int | None:
        if not style:
            return None
        lowered = style.lower()
        if not lowered.startswith("heading"):
            return None
        suffix = lowered.replace("heading", "", 1)
        if not suffix.isdigit():
            return None
        level = int(suffix)
        return level if level > 0 else None
