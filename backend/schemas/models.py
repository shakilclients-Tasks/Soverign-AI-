"""Ollama model discovery and configuration contracts."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str
    display_name: str = ""
    size_bytes: int = 0
    size_formatted: str = "0 B"
    family: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    kind: str
    deployment: Literal["local", "cloud"] = "local"


class ModelsResponse(BaseModel):
    ollama_connected: bool
    chat_models: List[ModelInfo]
    embedding_models: List[ModelInfo]
    active_chat_model: Optional[str] = None
    active_embedding_model: Optional[str] = None
    warning: Optional[str] = None


class ModelSettingsUpdate(BaseModel):
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    context_window: int = Field(8192, ge=8192, le=262_144)
    ollama_url: str


class RuntimeSettingsResponse(ModelSettingsUpdate):
    available_chat_models: List[ModelInfo] = Field(default_factory=list)
    available_embedding_models: List[ModelInfo] = Field(default_factory=list)
