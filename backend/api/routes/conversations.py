"""Persistent conversation history routes."""

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.dependencies import current_user
from backend.schemas.identity import UserResponse
from backend.schemas.chat import ConversationDetail, ConversationSummary
from backend.services.conversation_service import conversation_service


router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    _: UserResponse = Depends(current_user),
) -> List[ConversationSummary]:
    return await asyncio.to_thread(conversation_service.list_conversations, limit, search)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    _: UserResponse = Depends(current_user),
) -> ConversationDetail:
    result = await asyncio.to_thread(conversation_service.get_conversation, conversation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return result


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    _: UserResponse = Depends(current_user),
) -> None:
    deleted = await asyncio.to_thread(conversation_service.delete_conversation, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
