"""Semantic chunking: group parsed blocks by section, bounded by a max size."""

from dataclasses import dataclass

from ingestion.parse import ParsedBlock

MAX_CHUNK_CHARS = 1500


@dataclass
class Chunk:
    text: str
    section: str | None
    page: int | None


def chunk_blocks(blocks: list[ParsedBlock]) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_texts: list[str] = []
    current_section: str | None = None
    current_page: int | None = None

    for block in blocks:
        exceeds_size = sum(len(t) for t in current_texts) > MAX_CHUNK_CHARS
        section_changed = bool(current_texts) and block.section != current_section
        if current_texts and (exceeds_size or section_changed):
            chunks.append(Chunk(text=" ".join(current_texts), section=current_section, page=current_page))
            current_texts = []

        if not current_texts:
            current_section = block.section
            current_page = block.page
        current_texts.append(block.text)

    if current_texts:
        chunks.append(Chunk(text=" ".join(current_texts), section=current_section, page=current_page))

    return chunks
