"""Layout-aware PDF parsing via Docling: text blocks tagged with section and page."""

from dataclasses import dataclass
from pathlib import Path

from docling.datamodel.base_models import DocItemLabel
from docling.document_converter import DocumentConverter


@dataclass
class ParsedBlock:
    text: str
    section: str | None
    page: int | None


def parse_pdf(pdf_path: Path) -> list[ParsedBlock]:
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    document = result.document

    blocks: list[ParsedBlock] = []
    current_section: str | None = None

    for item, _level in document.iterate_items():
        text = getattr(item, "text", None)
        if not text:
            continue

        if item.label == DocItemLabel.SECTION_HEADER:
            current_section = text
            continue

        page = item.prov[0].page_no if item.prov else None
        blocks.append(ParsedBlock(text=text, section=current_section, page=page))

    return blocks
