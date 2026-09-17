"""Ingestion run orchestration: discover -> parse -> chunk -> embed -> store."""

import uuid
from pathlib import Path

from ingestion.chunk import chunk_blocks
from ingestion.discover import discover_new_pdfs
from ingestion.embed import embed_texts
from ingestion.parse import parse_pdf
from storage import metadata_db, vector_store


def ingest_pdf(path: Path, file_hash: str) -> str:
    document_id = str(uuid.uuid4())
    try:
        blocks = parse_pdf(path)
        chunks = chunk_blocks(blocks)
        if not chunks:
            raise ValueError("No extractable text found in PDF")

        embeddings = embed_texts([c.text for c in chunks])
        chunk_ids = [f"{document_id}:{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "document_id": document_id,
                "title": path.stem,
                "section": c.section or "",
                "page": c.page or 0,
                "source": "local",
            }
            for c in chunks
        ]

        vector_store.add_chunks(
            chunk_ids=chunk_ids,
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=metadatas,
        )

        # Title is a filename placeholder for plain-folder ingestion; Zotero-sourced
        # items use the richer metadata from Zotero instead (see storage.metadata_db).
        metadata_db.insert_document(
            document_id=document_id,
            title=path.stem,
            authors=None,
            doi=None,
            year=None,
            journal=None,
            source="local",
            file_path=str(path),
            zotero_key=None,
            file_hash=file_hash,
        )
        metadata_db.log_ingestion(document_id, status="success")
        return document_id
    except Exception as exc:
        metadata_db.log_ingestion(document_id, status="failed", error_message=str(exc))
        raise


def run_ingestion() -> list[str]:
    metadata_db.init_db()
    ingested_ids = []
    for discovered in discover_new_pdfs():
        document_id = ingest_pdf(discovered.path, discovered.file_hash)
        ingested_ids.append(document_id)
    return ingested_ids


if __name__ == "__main__":
    ids = run_ingestion()
    print(f"Ingested {len(ids)} document(s): {ids}")
