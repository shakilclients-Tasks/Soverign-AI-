"""Structured health status shown by the unobtrusive UI indicator."""

from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    backend: str
    ollama: str
    database: str
    vector_database: str
    chat_model: Optional[str] = None
    chat_deployment: str = "local"
    embedding_model: Optional[str] = None
    chat_ready: bool
    knowledge_ready: bool
    warning: Optional[str] = None
    version: str
