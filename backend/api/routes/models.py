"""Detected Ollama models and persisted runtime settings."""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import current_user
from backend.schemas.identity import UserResponse
from backend.schemas.models import ModelSettingsUpdate, ModelsResponse, RuntimeSettingsResponse
from backend.services.ollama_service import (
    EmbeddingUnavailableError,
    ModelUnavailableError,
    ollama_service,
)


router = APIRouter(tags=["Models and Settings"])


@router.get("/api/models", response_model=ModelsResponse)
async def models(refresh: bool = False) -> ModelsResponse:
    return await ollama_service.get_models_response(refresh=refresh)


@router.get("/api/settings/models", response_model=RuntimeSettingsResponse)
async def model_settings(_: UserResponse = Depends(current_user)) -> RuntimeSettingsResponse:
    return await ollama_service.runtime_settings()


@router.put("/api/settings/models", response_model=RuntimeSettingsResponse)
async def update_model_settings(
    request: ModelSettingsUpdate,
    _: UserResponse = Depends(current_user),
) -> RuntimeSettingsResponse:
    try:
        return await ollama_service.update_settings(
            request.chat_model,
            request.embedding_model,
            request.temperature,
            request.context_window,
            request.ollama_url,
        )
    except (ModelUnavailableError, EmbeddingUnavailableError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
