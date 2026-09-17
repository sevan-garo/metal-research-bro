"""SQLite metadata store: documents and ingestion_log tables."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,
    doi TEXT,
    year INTEGER,
    journal TEXT,
    source TEXT NOT NULL,
    file_path TEXT,
    zotero_key TEXT,
    ingested_at TEXT NOT NULL,
    file_hash TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    timestamp TEXT NOT NULL
);
"""


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.METADATA_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def is_ingested(file_hash: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM documents WHERE file_hash = ?", (file_hash,)).fetchone()
        return row is not None


def insert_document(
    document_id: str,
    title: str | None,
    authors: str | None,
    doi: str | None,
    year: int | None,
    journal: str | None,
    source: str,
    file_path: str | None,
    zotero_key: str | None,
    file_hash: str | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents
                (document_id, title, authors, doi, year, journal, source,
                 file_path, zotero_key, ingested_at, file_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                title,
                authors,
                doi,
                year,
                journal,
                source,
                file_path,
                zotero_key,
                datetime.now(timezone.utc).isoformat(),
                file_hash,
            ),
        )


def log_ingestion(document_id: str, status: str, error_message: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ingestion_log (document_id, status, error_message, timestamp) VALUES (?, ?, ?, ?)",
            (document_id, status, error_message, datetime.now(timezone.utc).isoformat()),
        )


def get_document(document_id: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,)).fetchone()
