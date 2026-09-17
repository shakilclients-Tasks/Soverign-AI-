"""Cancellation-aware SSE endpoint for every assistant request."""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.api.dependencies import current_user
from backend.core.logging import get_logger
from backend.schemas.identity import UserResponse
from backend.schemas.chat import StreamChatRequest
from backend.services.ollama_service import (
    CloudAccessRequiredError,
    ModelUnavailableError,
    NoChatModelError,
    OllamaError,
    OllamaOfflineError,
)
from backend.services.unified_ai_service import unified_ai_service


logger = get_logger("sovereign.chat")
router = APIRouter(prefix="/api/chat", tags=["Unified Chat"])


def _event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream_chat(
    payload: StreamChatRequest,
    request: Request,
    _: UserResponse = Depends(current_user),
) -> StreamingResponse:
    async def generate():
        try:
            async for event in unified_ai_service.stream_conversation(
                payload.conversation_id,
                payload.message,
                payload.attachment_ids,
                payload.knowledge_base_id,
                payload.model,
            ):
                if await request.is_disconnected():
                    raise asyncio.CancelledError
                yield _event(event)
        except asyncio.CancelledError:
            logger.info("Chat stream cancelled by client")
        except OllamaOfflineError:
            yield _event({"type": "error", "code": "OLLAMA_OFFLINE", "message": "Local AI service is offline."})
        except NoChatModelError:
            yield _event({"type": "error", "code": "NO_CHAT_MODEL", "message": "No compatible conversational model was detected in Ollama."})
        except ModelUnavailableError:
            yield _event({"type": "error", "code": "MODEL_UNAVAILABLE", "message": "Your configured local chat model is not installed. Open Settings → AI Model and select a detected model."})
        except CloudAccessRequiredError as exc:
            yield _event({"type": "error", "code": "CLOUD_ACCESS_REQUIRED", "message": str(exc)})
        except KeyError as exc:
            yield _event({"type": "error", "code": "NOT_FOUND", "message": str(exc).strip("'")})
        except OllamaError as exc:
            logger.warning("Local generation failed: %s", exc)
            yield _event({"type": "error", "code": "GENERATION_FAILED", "message": str(exc)})
        except Exception as exc:
            logger.exception("Unexpected unified chat failure: %s", exc)
            yield _event({"type": "error", "code": "CHAT_FAILED", "message": "Sovereign AI could not complete this request."})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
