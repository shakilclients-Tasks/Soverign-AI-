"""Knowledge collection contracts."""

from typing import List, Optional

from pydantic import BaseModel, Field


class KnowledgeCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field("", max_length=500)
    embedding_model: Optional[str] = None


class KnowledgeDocument(BaseModel):
    id: str
    filename: str
    status: str
    indexed_chunks: int
    created_at: str


class KnowledgeSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    embedding_model: str
    document_count: int
    total_chunks: int
    created_at: str
    updated_at: str
    documents: List[KnowledgeDocument] = Field(default_factory=list)


class KnowledgeUploadResponse(BaseModel):
    document: KnowledgeDocument
