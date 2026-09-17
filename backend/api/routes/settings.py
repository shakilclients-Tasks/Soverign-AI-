"""Low-priority diagnostics exposed only inside Settings."""

import asyncio
import platform
from typing import Any, Dict, List

import psutil
from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import current_user
from backend.core.config import settings
from backend.schemas.identity import UserResponse
from backend.services.conversation_service import conversation_service
from backend.services.ocr_service import ocr_service
from backend.services.ollama_service import ollama_service
from backend.services.sandbox_service import sandbox_service


router = APIRouter(prefix="/api/settings", tags=["Settings Diagnostics"])


def _system_info() -> Dict[str, Any]:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(settings.data_dir))
    return {
        "platform": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "ocr_available": ocr_service.available(),
        "ocr_backend": ocr_service.backend_name(),
        "docker_sandbox_available": sandbox_service.available(),
        "air_gapped": (
            settings.air_gapped_mode
            and ollama_service.active_chat_deployment() == "local"
        ),
    }


@router.get("/system")
async def system(_: UserResponse = Depends(current_user)) -> Dict[str, Any]:
    return await asyncio.to_thread(_system_info)


@router.get("/audit")
async def audit(
    limit: int = Query(50, ge=1, le=200),
    _: UserResponse = Depends(current_user),
) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(conversation_service.list_audit_logs, limit)
