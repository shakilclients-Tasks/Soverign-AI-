import json

import pytest

from backend.api.routes.chat import _event
from backend.schemas.models import ModelInfo
from backend.services.conversation_service import conversation_service, conversation_title
from backend.services.ollama_service import ModelUnavailableError, OllamaService, is_embedding_name
from backend.services.unified_ai_service import (
    _explicit_code_request,
    _explicit_knowledge_request,
    _python_block,
)


def test_model_categories_never_mix() -> None:
    service = OllamaService()
    service._models = [
        ModelInfo(name="qwen3.5:4b", kind="chat"),
        ModelInfo(name="nomic-embed-text:latest", kind="embedding"),
    ]
    service._active_chat_model = "qwen3.5:4b"
    service._active_embedding_model = "nomic-embed-text:latest"

    assert [model.name for model in service.list_chat_models()] == ["qwen3.5:4b"]
    assert [model.name for model in service.list_embedding_models()] == ["nomic-embed-text:latest"]
    assert service.resolve_chat_model() == "qwen3.5:4b"
    assert is_embedding_name("nomic-embed-text:latest")
    with pytest.raises(ModelUnavailableError):
        service.resolve_chat_model("nomic-embed-text:latest")


def test_deterministic_routes_require_explicit_intent() -> None:
    assert _explicit_code_request("Run this Python code")
    assert not _explicit_code_request("Explain this Python code")
    assert _python_block("Run this:\n```python\nprint('ok')\n```") == "print('ok')"
    assert _explicit_knowledge_request("Search our internal standards")
    assert not _explicit_knowledge_request("Explain air-gap isolation")


def test_sse_event_uses_real_frame_boundaries() -> None:
    encoded = _event({"type": "token", "content": "hello"})
    assert encoded.endswith("\n\n")
    assert "\\n\\n" not in encoded
    assert json.loads(encoded.removeprefix("data: ").strip())["content"] == "hello"


def test_conversation_is_created_once_and_messages_append(isolated_storage) -> None:
    conversation = conversation_service.create_conversation("  First\n useful   prompt  ", "chat-model")
    for role, content in (
        ("user", "Hi"),
        ("assistant", "Hello"),
        ("user", "Continue"),
        ("assistant", "Done"),
    ):
        conversation_service.add_message(conversation["id"], role, content, "chat-model")

    listed = conversation_service.list_conversations()
    detail = conversation_service.get_conversation(conversation["id"])
    assert conversation_title("  First\n useful   prompt  ") == "First useful prompt"
    assert len(listed) == 1
    assert listed[0]["message_count"] == 4
    assert detail is not None
    assert [message["role"] for message in detail["messages"]] == [
        "user", "assistant", "user", "assistant"
    ]
