"""Truthful health checks for local services."""

import asyncio

from fastapi import APIRouter

from backend.core.config import settings
from backend.db.database import get_db_connection
from backend.schemas.health import HealthResponse
from backend.services.ollama_service import ollama_service
from backend.services.vector_service import vector_service


router = APIRouter(tags=["Health"])


def _database_healthy() -> bool:
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


@router.get("/api/health", response_model=HealthResponse)
@router.get("/health", response_model=HealthResponse, include_in_schema=False)
async def health() -> HealthResponse:
    ollama, database_ok, vector_ok = await asyncio.gather(
        ollama_service.check_health(),
        asyncio.to_thread(_database_healthy),
        vector_service.check_health(),
    )
    chat_ready = bool(ollama["connected"] and ollama_service._active_chat_model)
    knowledge_ready = bool(
        vector_ok and ollama["connected"] and ollama_service._active_embedding_model
    )
    return HealthResponse(
        backend="healthy",
        ollama="healthy" if ollama["connected"] else "offline",
        database="healthy" if database_ok else "degraded",
        vector_database="healthy" if vector_ok else "degraded",
        chat_model=ollama_service._active_chat_model,
        chat_deployment=ollama_service.active_chat_deployment(),
        embedding_model=ollama_service._active_embedding_model,
        chat_ready=chat_ready,
        knowledge_ready=knowledge_ready,
        warning=ollama_service.warning,
        version=settings.app_version,
    )
