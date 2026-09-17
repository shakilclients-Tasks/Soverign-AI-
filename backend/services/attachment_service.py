"""Attachment metadata and extracted-text storage for unified chat."""

import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.db.database import get_db_connection
from backend.services.conversation_service import utc_now
from backend.services.document_service import document_service


class AttachmentService:
    def create(self, content: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        if not content:
            raise ValueError("The selected file is empty.")
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise ValueError(f"Files must be {settings.max_upload_mb} MB or smaller.")
        document = document_service.ingest(content, filename, content_type)
        detail = document_service.get_document(document["id"])
        attachment_id = str(uuid.uuid4())
        now = utc_now()
        extracted = detail["full_text"] if detail else ""
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO attachments(
                    id, document_id, filename, stored_path, content_type, size_bytes,
                    sha256_hash, extracted_text, extraction_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attachment_id,
                    document["id"],
                    document["filename"],
                    document["stored_path"],
                    content_type or "application/octet-stream",
                    document["file_size_bytes"],
                    document["sha256_hash"],
                    extracted,
                    document["extraction_status"],
                    now,
                ),
            )
        return {
            "id": attachment_id,
            "filename": document["filename"],
            "content_type": content_type or "application/octet-stream",
            "size_bytes": document["file_size_bytes"],
            "extraction_status": document["extraction_status"],
            "document_id": document["id"],
            "created_at": now,
        }

    def get_many(self, attachment_ids: List[str]) -> List[Dict[str, Any]]:
        if not attachment_ids:
            return []
        placeholders = ",".join("?" for _ in attachment_ids)
        with get_db_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM attachments WHERE id IN ({placeholders})", attachment_ids
            ).fetchall()
        by_id = {row["id"]: dict(row) for row in rows}
        missing = [item for item in attachment_ids if item not in by_id]
        if missing:
            raise KeyError("One or more attachments could not be found.")
        return [by_id[item] for item in attachment_ids]

    def delete_unbound(self, attachment_id: str) -> bool:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT conversation_id FROM attachments WHERE id = ?", (attachment_id,)
            ).fetchone()
            if not row or row["conversation_id"]:
                return False
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        return True


attachment_service = AttachmentService()
