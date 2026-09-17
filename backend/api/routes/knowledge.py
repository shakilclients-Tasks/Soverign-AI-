"""Secondary knowledge collection management routes."""

import asyncio
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.api.dependencies import current_user
from backend.schemas.identity import UserResponse
from backend.schemas.knowledge import (
    KnowledgeCreateRequest,
    KnowledgeSummary,
    KnowledgeUploadResponse,
)
from backend.services.knowledge_base_service import knowledge_base_service


router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


@router.get("", response_model=List[KnowledgeSummary])
async def list_knowledge(_: UserResponse = Depends(current_user)) -> List[KnowledgeSummary]:
    return await asyncio.to_thread(knowledge_base_service.list)


@router.post("", response_model=KnowledgeSummary, status_code=status.HTTP_201_CREATED)
async def create_knowledge(
    request: KnowledgeCreateRequest,
    _: UserResponse = Depends(current_user),
) -> KnowledgeSummary:
    try:
        return await knowledge_base_service.create(
            request.name, request.description, request.embedding_model
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{knowledge_id}/documents", response_model=KnowledgeUploadResponse)
async def add_document(
    knowledge_id: str,
    file: UploadFile = File(...),
    _: UserResponse = Depends(current_user),
) -> KnowledgeUploadResponse:
    try:
        content = await file.read()
        document = await knowledge_base_service.add_document(
            knowledge_id,
            content,
            file.filename or "document",
            file.content_type or "application/octet-stream",
        )
        return KnowledgeUploadResponse(document=document)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'")) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{knowledge_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(
    knowledge_id: str,
    document_id: str,
    _: UserResponse = Depends(current_user),
) -> None:
    if not await knowledge_base_service.remove_document(knowledge_id, document_id):
        raise HTTPException(status_code=404, detail="Knowledge document not found.")


@router.delete("/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    knowledge_id: str,
    _: UserResponse = Depends(current_user),
) -> None:
    if not await knowledge_base_service.delete(knowledge_id):
        raise HTTPException(status_code=404, detail="Knowledge collection not found.")
