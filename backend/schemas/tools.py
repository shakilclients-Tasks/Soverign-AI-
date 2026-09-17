"""Explicit local tool execution contracts."""

from typing import Optional

from pydantic import BaseModel, Field


class CodeExecutionRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100_000)
    language: str = "python"
    timeout_seconds: int = Field(10, ge=1, le=30)
    conversation_id: Optional[str] = None


class CodeExecutionResponse(BaseModel):
    id: str
    status: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    runtime_mode: str = "DOCKER_CONTAINER"
