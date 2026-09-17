"""Pure-logic tests for ingestion/chunk.py — no PDF parsing, no I/O."""

from ingestion.chunk import MAX_CHUNK_CHARS, chunk_blocks
from ingestion.parse import ParsedBlock


def test_splits_on_section_change():
    blocks = [
        ParsedBlock(text="abstract text", section="Abstract", page=1),
        ParsedBlock(text="intro text", section="Introduction", page=2),
    ]
    chunks = chunk_blocks(blocks)
    assert [c.section for c in chunks] == ["Abstract", "Introduction"]


def test_splits_when_section_exceeds_size_cap():
    long_text = "x" * (MAX_CHUNK_CHARS + 100)
    blocks = [
        ParsedBlock(text=long_text, section="Results", page=1),
        ParsedBlock(text="more results text", section="Results", page=1),
    ]
    chunks = chunk_blocks(blocks)
    assert len(chunks) == 2
    assert all(c.section == "Results" for c in chunks)


def test_excludes_reference_and_acknowledgment_sections():
    blocks = [
        ParsedBlock(text="real content", section="Discussion", page=5),
        ParsedBlock(text="Smith et al. 2020", section="VII. References", page=10),
        ParsedBlock(text="Thanks to funding body", section="Acknowledgements", page=11),
    ]
    chunks = chunk_blocks(blocks)
    assert len(chunks) == 1
    assert chunks[0].section == "Discussion"


def test_handles_missing_section():
    blocks = [ParsedBlock(text="orphan text", section=None, page=1)]
    chunks = chunk_blocks(blocks)
    assert len(chunks) == 1
    assert chunks[0].section is None


def test_empty_input_produces_no_chunks():
    assert chunk_blocks([]) == []
