"""Retrieval-only RAG service used by the unified chat orchestrator."""

from typing import Any, Dict, List

from backend.db.database import get_db_connection
from backend.services.vector_service import vector_service


class RAGService:
    async def retrieve(
        self, knowledge_base_id: str, query: str, top_k: int = 5
    ) -> Dict[str, List[Any]]:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT id, slug, name FROM knowledge_bases WHERE id = ? OR slug = ?",
                (knowledge_base_id, knowledge_base_id),
            ).fetchone()
        if not row:
            raise KeyError("Knowledge collection not found.")
        matches = await vector_service.search(row["slug"], query, top_k)
        contexts: List[str] = []
        sources: List[Dict[str, Any]] = []
        for match in matches:
            metadata = match["metadata"]
            contexts.append(match["document"])
            sources.append(
                {
                    "id": metadata.get("doc_id"),
                    "title": metadata.get("filename") or row["name"],
                    "page": metadata.get("page_number"),
                    "type": "knowledge",
                    "snippet": match["document"][:280],
                }
            )
        return {"contexts": contexts, "sources": sources}


rag_service = RAGService()
