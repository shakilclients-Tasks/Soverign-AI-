"""Multipart attachment ingestion for the unified composer."""

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.api.dependencies import current_user
from backend.schemas.identity import UserResponse
from backend.schemas.chat import AttachmentResponse
from backend.services.attachment_service import attachment_service


router = APIRouter(prefix="/api/attachments", tags=["Attachments"])


@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...),
    _: UserResponse = Depends(current_user),
) -> AttachmentResponse:
    try:
        content = await file.read()
        return await asyncio.to_thread(
            attachment_service.create,
            content,
            file.filename or "attachment",
            file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: str,
    _: UserResponse = Depends(current_user),
) -> None:
    deleted = await asyncio.to_thread(attachment_service.delete_unbound, attachment_id)
    if not deleted:
        raise HTTPException(status_code=409, detail="Attachment is already in use or does not exist.")
