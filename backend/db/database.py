"""SQLite connection handling and non-destructive schema migrations."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from backend.core.config import settings
from backend.core.logging import get_logger


logger = get_logger("sovereign.database")


def get_db_path() -> Path:
    path = Path(settings.sqlite_db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(get_db_path()), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn: sqlite3.Connection, table: str, declaration: str) -> None:
    name = declaration.split()[0]
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {declaration}")


def init_db() -> None:
    """Create the v3 schema while preserving existing project data."""
    with get_db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'General',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                tokens_per_second REAL,
                eval_duration_ms REAL,
                total_duration_ms REAL,
                citations_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                message_id TEXT,
                document_id TEXT,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256_hash TEXT NOT NULL,
                extracted_text TEXT NOT NULL DEFAULT '',
                extraction_status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS tool_executions (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                message_id TEXT,
                tool_name TEXT NOT NULL,
                request_summary TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                result_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                sha256_hash TEXT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 1,
                char_count INTEGER NOT NULL DEFAULT 0,
                word_count INTEGER NOT NULL DEFAULT 0,
                extraction_status TEXT NOT NULL DEFAULT 'COMPLETED',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS document_pages (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                text_content TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                image_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                domain TEXT NOT NULL DEFAULT 'General',
                classification_level TEXT NOT NULL DEFAULT 'UNCLASSIFIED',
                embedding_model TEXT NOT NULL,
                distance_metric TEXT NOT NULL DEFAULT 'cosine',
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_base_documents (
                id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                indexed_chunks INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'INDEXED',
                created_at TEXT NOT NULL,
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_attachments_conversation ON attachments(conversation_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_tool_executions_conversation ON tool_executions(conversation_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_document_hash ON documents(sha256_hash);
            CREATE INDEX IF NOT EXISTS idx_document_pages_document ON document_pages(document_id, page_number);
            CREATE INDEX IF NOT EXISTS idx_kb_documents_kb ON knowledge_base_documents(kb_id);
            """
        )
        _add_column(conn, "messages", "metadata_json TEXT NOT NULL DEFAULT '{}'")
    logger.info("SQLite schema ready at %s", get_db_path())


def get_setting(key: str) -> str | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str, updated_at: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, updated_at),
        )
