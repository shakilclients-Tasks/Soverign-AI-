"""Reusable asynchronous bridge to the local Ollama runtime."""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.db.database import get_setting, set_setting
from backend.schemas.models import ModelInfo, ModelsResponse, RuntimeSettingsResponse


logger = get_logger("sovereign.ollama")

EMBEDDING_MARKERS = (
    "nomic-embed",
    "mxbai-embed",
    "bge-",
    "all-minilm",
    "snowflake-arctic-embed",
    "text-embedding",
    "embeddinggemma",
)


class OllamaError(RuntimeError):
    code = "OLLAMA_ERROR"


class OllamaOfflineError(OllamaError):
    code = "OLLAMA_OFFLINE"


class NoChatModelError(OllamaError):
    code = "NO_CHAT_MODEL"


class ModelUnavailableError(OllamaError):
    code = "MODEL_UNAVAILABLE"


class EmbeddingUnavailableError(OllamaError):
    code = "EMBEDDING_UNAVAILABLE"


class CloudAccessRequiredError(OllamaError):
    code = "CLOUD_ACCESS_REQUIRED"


def is_embedding_name(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in EMBEDDING_MARKERS)


def is_cloud_name(name: str) -> bool:
    return name.lower().endswith(":cloud")


def format_model_display_name(name: str) -> str:
    """Format model identifiers into clean, Sovereign-branded display names.
    
    Ensures internal base model names (such as Qwen) are masked into Sovereign LLM.
    """
    if not name:
        return "Sovereign LLM"
    lowered = name.lower()
    if "sovereign-llm" in lowered:
        if "pro" in lowered or "precision" in lowered:
            return "Sovereign LLM Pro"
        if "fast" in lowered:
            return "Sovereign LLM Fast"
        return "Sovereign LLM"
    if "sovereign-doc-expert" in lowered:
        return "Sovereign LLM (Document Expert)"
    if "qwen" in lowered:
        if "0.8b" in lowered or "0.5b" in lowered or "1.5b" in lowered:
            return "Sovereign LLM (Fast)"
        if "4b" in lowered or "7b" in lowered or "14b" in lowered:
            return "Sovereign LLM (Precision)"
        return "Sovereign LLM"
    if "glm" in lowered:
        return "GLM-5.3 Flash (Cloud)" if ":cloud" in lowered else "GLM-5.3 Flash"
    if "nomic" in lowered:
        return "Nomic Embed Text"
    if "bge" in lowered:
        return "BGE Embed"
    if "minilm" in lowered:
        return "MiniLM Embed"
    return name


def format_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def _local_url(value: str) -> str:
    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Ollama URL must point to localhost")
    return normalized


def normalize_context_window(value: Any) -> int:
    """Keep enough prompt and output space to prevent mid-sentence document answers."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = settings.ollama_context_window
    return max(settings.ollama_min_context_window, min(parsed, 262_144))


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self._client: Optional[httpx.AsyncClient] = None
        self._models: List[ModelInfo] = []
        self._active_chat_model: Optional[str] = None
        self._active_embedding_model: Optional[str] = None
        self.temperature = 0.2
        self.context_window = normalize_context_window(settings.ollama_context_window)
        self.warning: Optional[str] = None
        self._lock = asyncio.Lock()

    def _new_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=settings.ollama_connect_timeout_seconds,
            read=settings.ollama_read_timeout_seconds,
            write=30.0,
            pool=5.0,
        )
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            trust_env=False,
        )

    async def start(self) -> None:
        saved_url = get_setting("ollama_url")
        if saved_url:
            try:
                self.base_url = _local_url(saved_url)
            except ValueError:
                logger.warning("Ignored invalid stored Ollama URL")
        self.temperature = float(get_setting("temperature") or 0.2)
        saved_context = get_setting("context_window")
        self.context_window = normalize_context_window(
            saved_context or settings.ollama_context_window
        )
        if saved_context != str(self.context_window):
            set_setting(
                "context_window",
                str(self.context_window),
                datetime.now(timezone.utc).isoformat(),
            )
            if saved_context:
                logger.warning(
                    "Raised unsafe saved context window from %s to %s",
                    saved_context,
                    self.context_window,
                )
        self._client = self._new_client()
        await self.refresh_models()
        configured_chat = get_setting("chat_model") or settings.chat_model
        configured_embedding = get_setting("embedding_model") or settings.embedding_model
        await self._resolve_configured_models(configured_chat, configured_embedding)
        logger.info(
            "Ollama connected=%s chat_model=%s embedding_model=%s",
            bool(self._models),
            self._active_chat_model,
            self._active_embedding_model,
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = self._new_client()
        return self._client

    async def check_health(self) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=4.0)
            response.raise_for_status()
            version = None
            try:
                version_response = await client.get("/api/version", timeout=2.0)
                if version_response.is_success:
                    version = version_response.json().get("version")
            except httpx.HTTPError:
                pass
            return {
                "connected": True,
                "version": version,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return {"connected": False, "version": None, "latency_ms": None}

    async def _model_capabilities(self, name: str) -> List[str]:
        try:
            client = await self._get_client()
            response = await client.post("/api/show", json={"model": name}, timeout=8.0)
            if not response.is_success:
                return []
            data = response.json()
            capabilities = data.get("capabilities") or []
            return [str(item).lower() for item in capabilities]
        except (httpx.HTTPError, ValueError):
            return []

    async def refresh_models(self) -> List[ModelInfo]:
        async with self._lock:
            try:
                client = await self._get_client()
                response = await client.get("/api/tags", timeout=6.0)
                response.raise_for_status()
                raw_models = response.json().get("models", [])
                capabilities = await asyncio.gather(
                    *(self._model_capabilities(item.get("name", "")) for item in raw_models)
                )
                discovered: List[ModelInfo] = []
                for raw, caps in zip(raw_models, capabilities):
                    name = raw.get("name") or raw.get("model")
                    if not name:
                        continue
                    details = raw.get("details") or {}
                    embedding_only = is_embedding_name(name) or (
                        "embedding" in caps and "completion" not in caps
                    )
                    discovered.append(
                        ModelInfo(
                            name=name,
                            display_name=format_model_display_name(name),
                            size_bytes=int(raw.get("size") or 0),
                            size_formatted=format_size(int(raw.get("size") or 0)),
                            family=details.get("family"),
                            parameter_size=details.get("parameter_size"),
                            quantization_level=details.get("quantization_level"),
                            capabilities=caps,
                            kind="embedding" if embedding_only else "chat",
                            deployment="cloud" if is_cloud_name(name) else "local",
                        )
                    )
                self._models = discovered
                return list(self._models)
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("Ollama model discovery failed: %s", exc)
                self._models = []
                self._active_chat_model = None
                self._active_embedding_model = None
                return []

    def list_models(self) -> List[ModelInfo]:
        return list(self._models)

    def list_chat_models(self) -> List[ModelInfo]:
        return [model for model in self._models if model.kind == "chat"]

    def list_embedding_models(self) -> List[ModelInfo]:
        return [model for model in self._models if model.kind == "embedding"]

    def active_chat_deployment(self) -> str:
        return (
            "cloud"
            if self._active_chat_model and is_cloud_name(self._active_chat_model)
            else "local"
        )

    async def _resolve_configured_models(
        self,
        configured_chat: Optional[str],
        configured_embedding: Optional[str],
    ) -> None:
        chat_names = [model.name for model in self.list_chat_models()]
        embedding_names = [model.name for model in self.list_embedding_models()]
        self.warning = None
        sovereign_candidates = [
            n for n in chat_names if "sovereign-llm" in n.lower()
        ]
        preferred_default = (
            sovereign_candidates[0] if sovereign_candidates else (chat_names[0] if chat_names else None)
        )
        if configured_chat and configured_chat in chat_names:
            self._active_chat_model = configured_chat
        elif preferred_default:
            self._active_chat_model = preferred_default
            if configured_chat:
                self.warning = (
                    f"Configured chat model '{configured_chat}' is not installed; "
                    f"using '{self._active_chat_model}'."
                )
        else:
            self._active_chat_model = None
            self.warning = "No compatible conversational model was detected in Ollama."

        self._active_embedding_model = (
            configured_embedding if configured_embedding in embedding_names else None
        )
        if configured_embedding and not self._active_embedding_model:
            embedding_warning = (
                "Embedding model is unavailable. Direct chat still works, but knowledge search is disabled."
            )
            self.warning = f"{self.warning} {embedding_warning}".strip() if self.warning else embedding_warning

    async def get_models_response(self, refresh: bool = False) -> ModelsResponse:
        health = await self.check_health()
        if refresh and health["connected"]:
            await self.refresh_models()
            await self._resolve_configured_models(
                get_setting("chat_model") or settings.chat_model,
                get_setting("embedding_model") or settings.embedding_model,
            )
        return ModelsResponse(
            ollama_connected=health["connected"],
            chat_models=self.list_chat_models(),
            embedding_models=self.list_embedding_models(),
            active_chat_model=self._active_chat_model,
            active_embedding_model=self._active_embedding_model,
            warning=self.warning,
        )

    def resolve_chat_model(self, requested: Optional[str] = None) -> str:
        names = {model.name for model in self.list_chat_models()}
        if requested:
            if requested not in names:
                raise ModelUnavailableError(
                    "The requested conversational model is not installed or is embedding-only."
                )
            return requested
        if not self._active_chat_model or self._active_chat_model not in names:
            raise NoChatModelError("No compatible conversational model was detected in Ollama.")
        return self._active_chat_model

    def resolve_embedding_model(self, requested: Optional[str] = None) -> str:
        names = {model.name for model in self.list_embedding_models()}
        target = requested or self._active_embedding_model
        if not target or target not in names:
            raise EmbeddingUnavailableError("The configured embedding model is unavailable.")
        return target

    async def update_settings(
        self,
        chat_model: Optional[str],
        embedding_model: Optional[str],
        temperature: float,
        context_window: int,
        ollama_url: str,
    ) -> RuntimeSettingsResponse:
        new_url = _local_url(ollama_url)
        if new_url != self.base_url:
            await self.close()
            self.base_url = new_url
            self._client = self._new_client()
        await self.refresh_models()
        chat_names = {model.name for model in self.list_chat_models()}
        embedding_names = {model.name for model in self.list_embedding_models()}
        if chat_model and chat_model not in chat_names:
            raise ModelUnavailableError("Selected chat model is not compatible or installed.")
        if embedding_model and embedding_model not in embedding_names:
            raise EmbeddingUnavailableError("Selected embedding model is not compatible or installed.")
        previous_chat_model = self._active_chat_model
        self._active_chat_model = chat_model
        self._active_embedding_model = embedding_model
        self.temperature = temperature
        self.context_window = normalize_context_window(context_window)
        now = datetime.now(timezone.utc).isoformat()
        for key, value in {
            "chat_model": chat_model or "",
            "embedding_model": embedding_model or "",
            "temperature": str(temperature),
            "context_window": str(self.context_window),
            "ollama_url": new_url,
        }.items():
            set_setting(key, value, now)
        if previous_chat_model and previous_chat_model != chat_model:
            await self.unload_model(previous_chat_model)
        if chat_model and previous_chat_model != chat_model:
            await self.warm_up()
        return await self.runtime_settings()

    async def runtime_settings(self) -> RuntimeSettingsResponse:
        return RuntimeSettingsResponse(
            chat_model=self._active_chat_model,
            embedding_model=self._active_embedding_model,
            temperature=self.temperature,
            context_window=self.context_window,
            ollama_url=self.base_url,
            available_chat_models=self.list_chat_models(),
            available_embedding_models=self.list_embedding_models(),
        )

    async def warm_up(self) -> None:
        try:
            model = self.resolve_chat_model()
            if is_cloud_name(model):
                logger.info("Skipped warm-up for cloud model: %s", model)
                return
            client = await self._get_client()
            await client.post(
                "/api/generate",
                json={
                    "model": model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": settings.ollama_keep_alive,
                    "options": {
                        "num_predict": 0,
                        "num_ctx": self.context_window,
                        "num_batch": settings.ollama_num_batch,
                    },
                },
            )
            logger.info("Ollama model warmed: %s", model)
        except Exception as exc:
            logger.warning("Ollama warm-up skipped: %s", exc)

    async def unload_model(self, model: str) -> None:
        """Release a previously selected model before loading a smaller one."""
        if is_cloud_name(model):
            return
        try:
            client = await self._get_client()
            await client.post(
                "/api/generate",
                json={
                    "model": model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": 0,
                    "options": {"num_predict": 0},
                },
            )
            logger.info("Ollama model unloaded: %s", model)
        except Exception as exc:
            logger.warning("Ollama model unload skipped for %s: %s", model, exc)

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        target = self.resolve_chat_model(model)
        payload = {
            "model": target,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": settings.ollama_num_predict,
            },
        }
        if not is_cloud_name(target):
            payload["think"] = False
            payload["keep_alive"] = settings.ollama_keep_alive
            payload["options"].update(
                {
                    "num_ctx": self.context_window,
                    "num_batch": settings.ollama_num_batch,
                }
            )
        try:
            client = await self._get_client()
            done_received = False
            async with client.stream("POST", "/api/chat", json=payload) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", errors="replace")[:500]
                    logger.error("Ollama chat failed status=%s body=%s", response.status_code, body)
                    if response.status_code in {401, 402, 403} and is_cloud_name(target):
                        raise CloudAccessRequiredError(
                            "GLM cloud access requires an eligible Ollama subscription or extra usage. "
                            "Enable cloud usage in your Ollama account, then retry."
                        )
                    if response.status_code == 404:
                        raise ModelUnavailableError(
                            "The configured chat model is no longer registered in Ollama."
                        )
                    raise OllamaError("Model generation failed.")
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("error"):
                        raise OllamaError(str(data["error"]))
                    content = (data.get("message") or {}).get("content") or ""
                    if content:
                        yield {"type": "token", "content": content}
                    if data.get("done"):
                        done_received = True
                        yield {
                            "type": "metrics",
                            "prompt_eval_count": data.get("prompt_eval_count"),
                            "eval_count": data.get("eval_count"),
                            "total_duration": data.get("total_duration"),
                            "done_reason": data.get("done_reason"),
                        }
                        break
            if not done_received:
                raise OllamaError(
                    "The model connection closed before generation completed. Please retry."
                )
        except httpx.ConnectError as exc:
            raise OllamaOfflineError("Local AI service is offline.") from exc
        except httpx.TimeoutException as exc:
            raise OllamaError("The local model timed out while generating a response.") from exc
        except httpx.HTTPError as exc:
            raise OllamaError(
                "The model connection was interrupted while generating a response. Please retry."
            ) from exc

    async def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        content = ""
        async for event in self.stream_chat(messages, model):
            if event["type"] == "token":
                content += event["content"]
        return content

    async def generate_embeddings(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[List[float]]:
        target = self.resolve_embedding_model(model)
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/embed",
                json={"model": target, "input": texts, "keep_alive": settings.ollama_keep_alive},
            )
            if response.status_code == 404 and len(texts) == 1:
                response = await client.post(
                    "/api/embeddings", json={"model": target, "prompt": texts[0]}
                )
                response.raise_for_status()
                return [response.json().get("embedding") or []]
            response.raise_for_status()
            embeddings = response.json().get("embeddings") or []
            if len(embeddings) != len(texts) or any(not item for item in embeddings):
                raise EmbeddingUnavailableError("Ollama returned incomplete embeddings.")
            return embeddings
        except httpx.ConnectError as exc:
            raise OllamaOfflineError("Local AI service is offline.") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingUnavailableError("Embedding generation failed.") from exc


ollama_service = OllamaService()
