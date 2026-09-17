"""SQLite-backed conversation, message, audit, and tool execution storage."""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.db.database import get_db_connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def conversation_title(message: str) -> str:
    clean = re.sub(r"\s+", " ", message).strip()
    if not clean:
        return "New conversation"
    return clean[:57] + "..." if len(clean) > 60 else clean


def _json(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _sources(value: str | None) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in _json(value, []):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": item.get("id") or item.get("doc_id"),
                "title": item.get("title") or item.get("file") or item.get("document_name") or "Local source",
                "page": item.get("page") or item.get("page_number"),
                "type": item.get("type", "document"),
                "snippet": item.get("snippet"),
            }
        )
    return normalized


class ConversationService:
    def create_conversation(self, title: str, model: Optional[str] = None) -> Dict[str, Any]:
        conversation_id = str(uuid.uuid4())
        now = utc_now()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations(id, title, model, mode, created_at, updated_at)
                VALUES (?, ?, ?, 'General', ?, ?)
                """,
                (conversation_id, conversation_title(title), model or "", now, now),
            )
        return {
            "id": conversation_id,
            "title": conversation_title(title),
            "model": model,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }

    def list_conversations(self, limit: int = 50, search: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT c.id, c.title, NULLIF(c.model, '') AS model, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
        """
        args: List[Any] = []
        if search:
            query += " WHERE LOWER(c.title) LIKE ?"
            args.append(f"%{search.lower()}%")
        query += " GROUP BY c.id ORDER BY c.updated_at DESC LIMIT ?"
        args.append(limit)
        with get_db_connection() as conn:
            rows = conn.execute(query, args).fetchall()
        return [dict(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            conversation = conn.execute(
                """
                SELECT id, title, NULLIF(model, '') AS model, created_at, updated_at
                FROM conversations WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if not conversation:
                return None
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at, rowid",
                (conversation_id,),
            ).fetchall()

        messages = []
        for row in rows:
            metadata = _json(row["metadata_json"] if "metadata_json" in row.keys() else None, {})
            messages.append(
                {
                    "id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "model": row["model"],
                    "sources": _sources(row["citations_json"]),
                    "metadata": metadata,
                    "created_at": row["created_at"],
                }
            )
        result = dict(conversation)
        result["message_count"] = len(messages)
        result["messages"] = messages
        return result

    def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        detail = self.get_conversation(conversation_id)
        messages = detail["messages"] if detail else []
        return messages[-limit:] if limit else messages

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if role not in {"user", "assistant", "system", "tool"}:
            raise ValueError("Unsupported message role")
        message_id = str(uuid.uuid4())
        now = utc_now()
        with get_db_connection() as conn:
            exists = conn.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
            if not exists:
                raise KeyError("Conversation not found")
            conn.execute(
                """
                INSERT INTO messages(
                    id, conversation_id, role, content, model, tokens_per_second,
                    eval_duration_ms, total_duration_ms, citations_json, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?)
                """,
                (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    model,
                    json.dumps(sources or []),
                    json.dumps(metadata or {}),
                    now,
                ),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ?, model = COALESCE(NULLIF(?, ''), model) WHERE id = ?",
                (now, model or "", conversation_id),
            )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "model": model,
            "sources": sources or [],
            "metadata": metadata or {},
            "created_at": now,
        }

    def bind_attachments(self, attachment_ids: List[str], conversation_id: str, message_id: str) -> None:
        if not attachment_ids:
            return
        placeholders = ",".join("?" for _ in attachment_ids)
        with get_db_connection() as conn:
            conn.execute(
                f"UPDATE attachments SET conversation_id = ?, message_id = ? WHERE id IN ({placeholders})",
                [conversation_id, message_id, *attachment_ids],
            )

    def delete_conversation(self, conversation_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        return cursor.rowcount > 0

    def log_audit_event(self, event_type: str, actor: str, details: str, status: str = "SUCCESS") -> None:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO audit_logs(id, event_type, actor, details, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), event_type, actor, details[:1000], status, utc_now()),
            )

    def list_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def record_tool_execution(
        self,
        tool_name: str,
        status: str,
        result: Dict[str, Any],
        conversation_id: Optional[str] = None,
        request_summary: str = "",
    ) -> str:
        execution_id = str(uuid.uuid4())
        now = utc_now()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO tool_executions(
                    id, conversation_id, tool_name, request_summary, status,
                    result_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    conversation_id,
                    tool_name,
                    request_summary[:500],
                    status,
                    json.dumps(result),
                    now,
                    now,
                ),
            )
        return execution_id


conversation_service = ConversationService()
