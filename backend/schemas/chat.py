"""Contracts for the single conversation API."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StreamChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=100_000)
    attachment_ids: List[str] = Field(default_factory=list)
    knowledge_base_id: Optional[str] = None
    model: Optional[str] = None


class SourceItem(BaseModel):
    id: Optional[str] = None
    title: str
    page: Optional[int] = None
    type: str
    snippet: Optional[str] = None


class MessageItem(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    model: Optional[str] = None
    sources: List[SourceItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    model: Optional[str] = None
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationDetail(ConversationSummary):
    messages: List[MessageItem] = Field(default_factory=list)


class AttachmentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    extraction_status: str
    document_id: Optional[str] = None
    created_at: str
