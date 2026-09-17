"""Explicit tool endpoints; capabilities are not separate assistant personas."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import current_user
from backend.schemas.identity import UserResponse
from backend.schemas.tools import CodeExecutionRequest, CodeExecutionResponse
from backend.services.sandbox_service import SandboxUnavailableError, sandbox_service


router = APIRouter(prefix="/api/tools", tags=["Local Tools"])


@router.post("/run-code", response_model=CodeExecutionResponse)
async def run_code(
    request: CodeExecutionRequest,
    _: UserResponse = Depends(current_user),
) -> CodeExecutionResponse:
    try:
        return await asyncio.to_thread(sandbox_service.execute, request)
    except SandboxUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
