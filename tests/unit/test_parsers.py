from io import BytesIO
from zipfile import ZipFile

import pytest

from app.services.parsers.base import UnsupportedFormatError
from app.services.parsers.docx_parser import DocxParser
from app.services.parsers.factory import ParserFactory
from app.services.parsers.html_parser import HtmlParser


def _build_minimal_docx_bytes() -> bytes:
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Section One</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Body paragraph text.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
"""
    with BytesIO() as stream:
        with ZipFile(stream, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
        return stream.getvalue()


def test_docx_parser_extracts_heading_context() -> None:
    parser = DocxParser()
    parsed = parser.parse(
        payload=_build_minimal_docx_bytes(),
        source_filename="sample.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert len(parsed.blocks) == 1
    assert parsed.blocks[0].content == "Body paragraph text."
    assert parsed.blocks[0].section_path == "Section One"
    assert parsed.blocks[0].title == "Section One"


def test_html_parser_extracts_text_blocks() -> None:
    parser = HtmlParser()
    html = (
        b"<html><head><title>Doc</title></head>"
        b"<body><h1>A</h1><p>First</p><p>Second</p></body></html>"
    )
    parsed = parser.parse(payload=html, source_filename="sample.html", mime_type="text/html")

    assert parsed.title == "Doc"
    assert [block.content for block in parsed.blocks] == ["First", "Second"]
    assert parsed.blocks[0].section_path == "A"


def test_parser_factory_rejects_unsupported_extension() -> None:
    factory = ParserFactory()

    with pytest.raises(UnsupportedFormatError):
        factory.parse_document(
            payload=b"binary",
            source_filename="sample.exe",
            mime_type="application/octet-stream",
        )
