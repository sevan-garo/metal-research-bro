"""Discover local PDFs not yet ingested, by content hash (idempotence)."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import config
from storage import metadata_db


@dataclass
class DiscoveredFile:
    path: Path
    file_hash: str


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_new_pdfs() -> list[DiscoveredFile]:
    metadata_db.init_db()
    discovered = []
    for pdf_path in sorted(config.PDF_DIR.glob("*.pdf")):
        file_hash = _hash_file(pdf_path)
        if not metadata_db.is_ingested(file_hash):
            discovered.append(DiscoveredFile(path=pdf_path, file_hash=file_hash))
    return discovered
