"""Small knowledge collection manager backed by SQLite and ChromaDB."""

import asyncio
import json
import re
import uuid
from typing import Any, Dict, List, Optional

from backend.db.database import get_db_connection
from backend.services.conversation_service import utc_now
from backend.services.document_service import document_service
from backend.services.ollama_service import ollama_service
from backend.services.vector_service import vector_service


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if len(slug) < 3:
        slug = f"knowledge-{slug or uuid.uuid4().hex[:6]}"
    return slug[:60]


class KnowledgeBaseService:
    async def create(
        self, name: str, description: str, embedding_model: Optional[str] = None
    ) -> Dict[str, Any]:
        target_model = embedding_model or ollama_service.resolve_embedding_model()
        if target_model in {model.name for model in ollama_service.list_embedding_models()}:
            ollama_service.resolve_embedding_model(target_model)
        base_slug = slugify(name)
        slug = base_slug
        with get_db_connection() as conn:
            counter = 2
            while conn.execute("SELECT id FROM knowledge_bases WHERE slug = ?", (slug,)).fetchone():
                slug = f"{base_slug}-{counter}"
                counter += 1
        await vector_service.create_collection(slug, target_model, description)
        knowledge_id = str(uuid.uuid4())
        now = utc_now()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_bases(
                    id, name, slug, description, domain, classification_level,
                    embedding_model, distance_metric, tags, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'General', 'UNCLASSIFIED', ?, 'cosine', '[]', ?, ?)
                """,
                (knowledge_id, name.strip(), slug, description.strip(), target_model, now, now),
            )
        return self.get(knowledge_id)

    def get(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_bases WHERE id = ? OR slug = ?",
                (knowledge_id, knowledge_id),
            ).fetchone()
            if not row:
                return None
            documents = conn.execute(
                """
                SELECT d.id, d.filename, k.status, k.indexed_chunks, k.created_at
                FROM knowledge_base_documents k
                JOIN documents d ON d.id = k.document_id
                WHERE k.kb_id = ? ORDER BY k.created_at DESC
                """,
                (row["id"],),
            ).fetchall()
        result = dict(row)
        result["documents"] = [dict(document) for document in documents]
        result["document_count"] = len(documents)
        result["total_chunks"] = sum(document["indexed_chunks"] for document in documents)
        return result

    def list(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            ids = [row["id"] for row in conn.execute(
                "SELECT id FROM knowledge_bases ORDER BY updated_at DESC"
            ).fetchall()]
        return [item for item in (self.get(item_id) for item_id in ids) if item]

    async def add_document(
        self, knowledge_id: str, content: bytes, filename: str, content_type: str
    ) -> Dict[str, Any]:
        knowledge = self.get(knowledge_id)
        if not knowledge:
            raise KeyError("Knowledge collection not found.")
        document = await asyncio.to_thread(document_service.ingest, content, filename, content_type)
        now = utc_now()
        try:
            chunks = await vector_service.index_document(knowledge["slug"], document["id"])
            status = "indexed"
        except Exception:
            chunks = 0
            status = "failed"
            raise
        finally:
            with get_db_connection() as conn:
                conn.execute(
                    "DELETE FROM knowledge_base_documents WHERE kb_id = ? AND document_id = ?",
                    (knowledge["id"], document["id"]),
                )
                conn.execute(
                    """
                    INSERT INTO knowledge_base_documents(
                        id, kb_id, document_id, indexed_chunks, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), knowledge["id"], document["id"], chunks, status, now),
                )
                conn.execute(
                    "UPDATE knowledge_bases SET updated_at = ? WHERE id = ?", (now, knowledge["id"])
                )
        return {
            "id": document["id"],
            "filename": document["filename"],
            "status": status,
            "indexed_chunks": chunks,
            "created_at": now,
        }

    async def remove_document(self, knowledge_id: str, document_id: str) -> bool:
        knowledge = self.get(knowledge_id)
        if not knowledge:
            return False
        with get_db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM knowledge_base_documents WHERE kb_id = ? AND document_id = ?",
                (knowledge["id"], document_id),
            )
            remaining = conn.execute(
                "SELECT COUNT(*) FROM knowledge_base_documents WHERE document_id = ?", (document_id,)
            ).fetchone()[0]
        if cursor.rowcount == 0:
            return False
        await vector_service.remove_document(knowledge["slug"], document_id)
        if remaining == 0:
            await asyncio.to_thread(document_service.delete_document, document_id)
        return True

    async def delete(self, knowledge_id: str) -> bool:
        knowledge = self.get(knowledge_id)
        if not knowledge:
            return False
        await vector_service.delete_collection(knowledge["slug"])
        with get_db_connection() as conn:
            conn.execute("DELETE FROM knowledge_bases WHERE id = ?", (knowledge["id"],))
        return True


knowledge_base_service = KnowledgeBaseService()
