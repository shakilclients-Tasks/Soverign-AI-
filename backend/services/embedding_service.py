"""Singleton local embedding service for Ollama and cached SentenceTransformers."""

import asyncio
from typing import Any, Dict, List, Optional

from backend.services.ollama_service import ollama_service


class EmbeddingService:
    def __init__(self) -> None:
        self._sentence_transformers: Dict[str, Any] = {}
        self._model_lock = asyncio.Lock()

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1400,
        overlap: int = 180,
    ) -> List[str]:
        clean = text.strip()
        if not clean:
            return []
        chunks: List[str] = []
        start = 0
        while start < len(clean):
            end = min(len(clean), start + chunk_size)
            if end < len(clean):
                boundary = max(
                    clean.rfind("\n\n", start, end),
                    clean.rfind(". ", start, end),
                    clean.rfind("\n", start, end),
                )
                if boundary > start + chunk_size // 2:
                    end = boundary + 1
            chunk = clean[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(clean):
                break
            start = max(start + 1, end - overlap)
        return chunks

    async def _sentence_transformer(self, model_name: str) -> Any:
        async with self._model_lock:
            if model_name in self._sentence_transformers:
                return self._sentence_transformers[model_name]

            def load() -> Any:
                from sentence_transformers import SentenceTransformer

                return SentenceTransformer(model_name, local_files_only=True)

            try:
                model = await asyncio.to_thread(load)
            except Exception as exc:
                raise RuntimeError(
                    f"SentenceTransformer '{model_name}' is not available in the local model cache."
                ) from exc
            self._sentence_transformers[model_name] = model
            return model

    async def embed_texts(
        self, texts: List[str], model_name: Optional[str] = None
    ) -> List[List[float]]:
        if not texts:
            return []
        ollama_embedding_names = {
            model.name for model in ollama_service.list_embedding_models()
        }
        target = model_name or ollama_service._active_embedding_model
        if target in ollama_embedding_names:
            return await ollama_service.generate_embeddings(texts, target)
        if not target:
            raise RuntimeError("No local embedding model is configured.")
        model = await self._sentence_transformer(target)

        def encode() -> List[List[float]]:
            values = model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return values.tolist()

        return await asyncio.to_thread(encode)


embedding_service = EmbeddingService()
