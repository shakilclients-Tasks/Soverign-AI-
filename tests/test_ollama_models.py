from backend.services.ollama_service import (
    format_model_display_name,
    is_cloud_name,
    is_embedding_name,
    normalize_context_window,
)


def test_model_deployment_classification() -> None:
    assert is_cloud_name("glm-5.3-flash:cloud")
    assert is_cloud_name("MODEL:CLOUD")
    assert not is_cloud_name("qwen3.5:0.8b")
    assert is_embedding_name("nomic-embed-text:latest")


def test_document_generation_context_has_safe_minimum() -> None:
    assert normalize_context_window(2048) == 8192
    assert normalize_context_window("invalid") >= 8192
    assert normalize_context_window(16_384) == 16_384


def test_sovereign_model_display_names() -> None:
    assert format_model_display_name("sovereign-llm") == "Sovereign LLM"
    assert format_model_display_name("sovereign-llm:latest") == "Sovereign LLM"
    assert format_model_display_name("sovereign-doc-expert") == "Sovereign LLM (Document Expert)"
    assert format_model_display_name("qwen3.5:0.8b") == "Sovereign LLM (Fast)"
    assert format_model_display_name("qwen3.5:4b") == "Sovereign LLM (Precision)"
    assert "qwen" not in format_model_display_name("qwen-custom").lower()
    assert format_model_display_name("nomic-embed-text:latest") == "Nomic Embed Text"

