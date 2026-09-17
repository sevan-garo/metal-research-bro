"""Semantic chunking: group parsed blocks by section, bounded by a max size."""

import re
from dataclasses import dataclass

from ingestion.parse import ParsedBlock

MAX_CHUNK_CHARS = 1500

# Reference lists repeat paper titles/keywords verbatim, which makes them
# score deceptively high against embedding queries built from those same
# keywords, while containing no answerable content themselves (see
# docs/adr/0011). Excluded from chunking entirely rather than just
# deprioritized, since they should never be cited as a claim's source.
# Matched as a substring (not equality) because real headings are rarely the
# bare word alone — e.g. "VII. References" or "Acknowledgements & Funding".
EXCLUDED_SECTION_KEYWORDS = ("references", "bibliography", "acknowledg")


@dataclass
class Chunk:
    text: str
    section: str | None
    page: int | None


def _is_excluded(section: str | None) -> bool:
    if not section:
        return False
    normalized = re.sub(r"[^a-z]", "", section.lower())
    return any(keyword in normalized for keyword in EXCLUDED_SECTION_KEYWORDS)


def chunk_blocks(blocks: list[ParsedBlock]) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_texts: list[str] = []
    current_section: str | None = None
    current_page: int | None = None

    for block in blocks:
        if _is_excluded(block.section):
            continue

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
