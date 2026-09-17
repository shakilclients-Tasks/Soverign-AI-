"""Persistent ChromaDB operations with explicit local embeddings."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.core.config import settings
from backend.services.document_service import document_service
from backend.services.embedding_service import embedding_service


class VectorService:
    def __init__(self) -> None:
        self._client: Optional[chromadb.ClientAPI] = None
        self._lock = asyncio.Lock()

    async def client(self) -> chromadb.ClientAPI:
        async with self._lock:
            if self._client is None:
                self._client = await asyncio.to_thread(
                    chromadb.PersistentClient,
                    path=str(settings.chroma_dir),
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            return self._client

    async def check_health(self) -> bool:
        try:
            client = await self.client()
            await asyncio.to_thread(client.heartbeat)
            return True
        except Exception:
            return False

    async def create_collection(
        self, name: str, embedding_model: str, description: str = ""
    ) -> None:
        client = await self.client()
        metadata = {
            "description": description,
            "embedding_model": embedding_model,
            "hnsw:space": "cosine",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(
            client.get_or_create_collection, name=name, metadata=metadata
        )

    async def delete_collection(self, name: str) -> None:
        client = await self.client()
        try:
            await asyncio.to_thread(client.delete_collection, name=name)
        except Exception:
            return

    async def index_document(self, collection_name: str, document_id: str) -> int:
        client = await self.client()
        collection = await asyncio.to_thread(client.get_collection, name=collection_name)
        model_name = (collection.metadata or {}).get("embedding_model")
        document = await asyncio.to_thread(document_service.get_document, document_id)
        if not document:
            raise ValueError("Document not found.")
        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        for page in document["pages"]:
            chunks = embedding_service.chunk_text(page["text_content"])
            for index, chunk in enumerate(chunks):
                ids.append(f"{document_id}:p{page['page_number']}:c{index}")
                texts.append(chunk)
                metadatas.append(
                    {
                        "doc_id": document_id,
                        "filename": document["filename"],
                        "page_number": int(page["page_number"]),
                        "chunk_index": index,
                    }
                )
        if not texts:
            raise ValueError("No extractable text was found in the document.")
        embeddings = await embedding_service.embed_texts(texts, model_name)
        await asyncio.to_thread(
            collection.upsert,
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    async def remove_document(self, collection_name: str, document_id: str) -> None:
        client = await self.client()
        collection = await asyncio.to_thread(client.get_collection, name=collection_name)
        await asyncio.to_thread(collection.delete, where={"doc_id": document_id})

    async def search(
        self, collection_name: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        client = await self.client()
        collection = await asyncio.to_thread(client.get_collection, name=collection_name)
        count = await asyncio.to_thread(collection.count)
        if count == 0:
            return []
        model_name = (collection.metadata or {}).get("embedding_model")
        query_embedding = (await embedding_service.embed_texts([query], model_name))[0]
        result = await asyncio.to_thread(
            collection.query,
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        rows: List[Dict[str, Any]] = []
        for index, item_id in enumerate((result.get("ids") or [[]])[0]):
            rows.append(
                {
                    "id": item_id,
                    "document": (result.get("documents") or [[]])[0][index],
                    "metadata": (result.get("metadatas") or [[]])[0][index] or {},
                    "distance": float((result.get("distances") or [[]])[0][index]),
                }
            )
        return rows


vector_service = VectorService()
