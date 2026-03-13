from app.services.chunking import ChunkingService
from app.services.parsers.base import ParsedBlock, ParsedDocument


def test_chunking_is_deterministic_and_propagates_metadata() -> None:
    source_text = " ".join(f"line-{idx}" for idx in range(200))
    parsed = ParsedDocument(
        source_filename="sample.txt",
        mime_type="text/plain",
        title="sample",
        raw_text=source_text,
        blocks=[
            ParsedBlock(
                content=source_text,
                title="section",
                section_path="Root > section",
                metadata={"parser": "txt"},
            )
        ],
        metadata={"doc_meta": "v1"},
    )
    chunking = ChunkingService(chunk_size_chars=120, chunk_overlap_chars=20)

    first = chunking.build_chunks(parsed)
    second = chunking.build_chunks(parsed)

    assert [chunk.content for chunk in first] == [chunk.content for chunk in second]
    assert len(first) > 1
    assert first[0].metadata["doc_meta"] == "v1"
    assert first[0].metadata["parser"] == "txt"
    assert first[0].metadata["source_block_index"] == 0

