"""Runtime configuration for the local Sovereign AI services."""

from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Collision-resistant settings loaded from ``SOVEREIGN_*`` variables."""

    app_name: str = "Sovereign AI"
    app_version: str = "3.0.0"
    app_env: str = "development"
    debug: bool = False

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    ollama_base_url: str = "http://127.0.0.1:11434"
    chat_model: Optional[str] = "sovereign-llm"
    embedding_model: Optional[str] = "nomic-embed-text:latest"
    ollama_connect_timeout_seconds: float = 4.0
    ollama_read_timeout_seconds: float = 300.0
    ollama_min_context_window: int = 8192
    ollama_keep_alive: str = "60m"
    ollama_context_window: int = 8192
    ollama_num_predict: int = 2048
    ollama_num_batch: int = 512

    data_dir: Path = PROJECT_ROOT / "data"
    uploads_dir: Path = PROJECT_ROOT / "data" / "uploads"
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma"
    sqlite_db_path: Path = PROJECT_ROOT / "data" / "database" / "sovereign.db"

    max_upload_mb: int = 25
    max_context_characters: int = 28_000
    conversation_history_messages: int = 8
    sandbox_image: str = "python:3.11-alpine"
    log_level: str = "INFO"
    air_gapped_mode: bool = True

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="SOVEREIGN_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("ollama_base_url")
    @classmethod
    def require_local_ollama(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Ollama URL must use http or https")
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Ollama must be bound to the local machine")
        return normalized

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.uploads_dir,
            self.chroma_dir,
            self.sqlite_db_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
