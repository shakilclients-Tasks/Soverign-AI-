"""One deterministic orchestration path for chat, documents, RAG, and tools."""

import asyncio
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.schemas.tools import CodeExecutionRequest
from backend.services.attachment_service import attachment_service
from backend.services.conversation_service import conversation_service
from backend.services.embedding_service import embedding_service
from backend.services.knowledge_base_service import knowledge_base_service
from backend.services.ollama_service import OllamaError, ollama_service
from backend.services.rag_service import rag_service
from backend.services.sandbox_service import SandboxUnavailableError, sandbox_service


logger = get_logger("sovereign.orchestrator")

SYSTEM_CONVERSATIONAL_INSTRUCTION = (
    "You are Sovereign AI, an advanced, highly intelligent AI assistant operating at the caliber of ChatGPT and Gemini.\n\n"
    "CORE DIRECTIVES:\n"
    "1. Comprehensive & Structured: Provide thorough, structured, and insightful answers with clear headings and bulleted takeaways.\n"
    "2. Tabular Presentation: Whenever presenting comparative data, metrics, or technical lists, format them using clean Markdown tables.\n"
    "3. Natural Communication: Answer directly and conversationally. NEVER output fake document citations or placeholders like [Document: <general knowledge>, Page N/A].\n"
    "4. Precision & Depth: Deliver accurate, production-ready explanations and code without artificial brevity."
)

SYSTEM_DOCUMENT_INSTRUCTION = (
    "You are Sovereign AI, an advanced AI assistant specialized in comprehensive document intelligence and knowledge synthesis.\n\n"
    "DOCUMENT ANALYSIS GUIDELINES:\n"
    "1. Deep Comprehension: Structure document analyses with an Executive Summary, Key Findings, and Actionable Items.\n"
    "2. Precision Citations: Cite ONLY when referencing facts or quotes from the uploaded files provided below, using the exact filename: [Document: filename, Page X].\n"
    "3. NO Placeholder Citations: NEVER output placeholders like '[Document: <general knowledge>, Page N/A]' or '[Document: <filename>]'. If a detail is general knowledge, do not cite a document.\n"
    "4. Tabular & Structured Presentation: Whenever presenting comparative data or metrics, format them using clean Markdown tables, bold headers, and bulleted lists.\n"
    "5. Grounding & Zero Hallucination: Ground your statements strictly in the provided document context. If a requested detail is not addressed in the documents, explicitly state that it is not mentioned in the provided materials."
)

SYSTEM_INSTRUCTION = SYSTEM_CONVERSATIONAL_INSTRUCTION


def clean_unwanted_citations(text: str) -> str:
    """Strip out hallucinated or placeholder citations like [Document: <general knowledge>, Page N/A]."""
    cleaned = re.sub(
        r"\s*\[Document:\s*(?:<[^>]+>|general\s+knowledge|n/?a|unknown|none)[^\]]*\]\s*([.,;])?",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r" +([.,;])", r"\1", cleaned)


class StreamingCitationSanitizer:
    """Filters out unwanted citation tags like [Document: <general knowledge>, Page N/A] from token streams."""

    def __init__(self):
        self.buffer = ""
        self.in_bracket = False

    def process(self, token: str) -> str:
        output = []
        for char in token:
            if char == "[":
                if self.buffer:
                    output.append(self.buffer)
                    self.buffer = ""
                self.in_bracket = True
                self.buffer += char
            elif self.in_bracket:
                self.buffer += char
                if char == "]":
                    self.in_bracket = False
                    cleaned = clean_unwanted_citations(self.buffer)
                    if cleaned:
                        output.append(cleaned)
                    self.buffer = ""
                elif len(self.buffer) > 120:
                    self.in_bracket = False
                    output.append(self.buffer)
                    self.buffer = ""
            else:
                self.buffer += char

        if not self.in_bracket and self.buffer:
            output.append(self.buffer)
            self.buffer = ""
        return "".join(output)

    def flush(self) -> str:
        if self.buffer:
            res = clean_unwanted_citations(self.buffer)
            self.buffer = ""
            return res
        return ""


def _explicit_code_request(message: str) -> bool:
    lowered = message.lower()
    has_action = bool(re.search(r"\b(run|execute)\b", lowered))
    has_code = bool(re.search(r"\b(python|code|script)\b", lowered))
    return has_action and has_code


def _explicit_knowledge_request(message: str) -> bool:
    """Route only clear internal-document searches to every indexed collection."""
    lowered = message.lower()
    has_search = bool(re.search(r"\b(search|find|look up|retrieve|from)\b", lowered))
    has_scope = bool(
        re.search(
            r"\b(knowledge|internal|organization(?:al)?|documents?|standards?|polic(?:y|ies)|manuals?|sops?)\b",
            lowered,
        )
    )
    return has_search and has_scope


def _python_block(message: str) -> Optional[str]:
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", message, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _bounded_context(parts: List[str], limit: int) -> str:
    selected: List[str] = []
    used = 0
    for part in parts:
        remaining = limit - used
        if remaining <= 0:
            break
        selected.append(part[:remaining])
        used += min(len(part), remaining)
    return "\n\n".join(selected)


def _select_relevant_document_sections(extracted: str, user_message: str, max_chars: int) -> str:
    """Preserve full text if within budget; otherwise extract document overview + query-relevant sections."""
    clean = extracted.strip()
    if len(clean) <= max_chars:
        return clean

    chunks = embedding_service.chunk_text(clean, chunk_size=1500, overlap=200)
    if not chunks:
        return clean[:max_chars]

    query_terms = set(re.findall(r"\w+", user_message.lower())) - {
        "the", "a", "an", "is", "are", "and", "or", "in", "on", "of", "to", "for", "with", "this", "that", "it"
    }

    scored: List[tuple[float, int, str]] = []
    for idx, chunk in enumerate(chunks):
        score = 0.0
        if idx == 0:
            score += 15.0  # Document header/first page
        elif idx == 1:
            score += 5.0
        if query_terms:
            chunk_lower = chunk.lower()
            matches = sum(1 for term in query_terms if term in chunk_lower)
            score += matches * 3.0
        scored.append((score, idx, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected_indices: set[int] = set()
    total_len = 0
    for _, idx, chunk in scored:
        if total_len + len(chunk) > max_chars:
            continue
        selected_indices.add(idx)
        total_len += len(chunk)
        if total_len >= max_chars * 0.95:
            break

    ordered = [chunks[i] for i in sorted(selected_indices)]
    return "\n\n[... sections omitted for length ...]\n\n".join(ordered)


class UnifiedAIService:
    async def stream_conversation(
        self,
        conversation_id: Optional[str],
        user_message: str,
        attachment_ids: Optional[List[str]] = None,
        knowledge_base_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        target_model = ollama_service.resolve_chat_model(model)
        existing = None
        if conversation_id:
            existing = await asyncio.to_thread(
                conversation_service.get_conversation, conversation_id
            )
            if not existing:
                raise KeyError("Conversation not found.")
        if not existing:
            existing = await asyncio.to_thread(
                conversation_service.create_conversation, user_message, target_model
            )
            conversation_id = existing["id"]
            yield {
                "type": "conversation",
                "conversation_id": conversation_id,
                "title": existing["title"],
            }

        prior_messages = await asyncio.to_thread(
            conversation_service.get_messages,
            conversation_id,
            settings.conversation_history_messages,
        )
        user_record = await asyncio.to_thread(
            conversation_service.add_message,
            conversation_id,
            "user",
            user_message,
            target_model,
            [],
            {"attachment_ids": attachment_ids or []},
        )
        await asyncio.to_thread(
            conversation_service.bind_attachments,
            attachment_ids or [],
            conversation_id,
            user_record["id"],
        )

        contexts: List[str] = []
        sources: List[Dict[str, Any]] = []
        warnings: List[str] = []
        routes: List[str] = []

        if attachment_ids:
            routes.append("documents")
            attachments = await asyncio.to_thread(
                attachment_service.get_many, attachment_ids
            )
            for attachment in attachments:
                extracted = attachment["extracted_text"].strip()
                if extracted:
                    per_doc_limit = max(4000, settings.max_context_characters // max(1, len(attachments)))
                    curated = _select_relevant_document_sections(extracted, user_message, per_doc_limit)
                    contexts.append(
                        f"[Attached document: {attachment['filename']}]\n{curated}"
                    )
                    sources.append(
                        {
                            "id": attachment["document_id"],
                            "title": attachment["filename"],
                            "page": None,
                            "type": "attachment",
                            "snippet": extracted[:350],
                        }
                    )
                else:
                    warnings.append(
                        f"No text could be extracted from {attachment['filename']}."
                    )

        knowledge_targets: List[str] = []
        if knowledge_base_id:
            knowledge_targets = [knowledge_base_id]
        elif _explicit_knowledge_request(user_message):
            collections = await asyncio.to_thread(knowledge_base_service.list)
            knowledge_targets = [
                item["id"] for item in collections if item["document_count"] > 0
            ][:8]
            if not knowledge_targets:
                warnings.append("No indexed knowledge collections are available to search.")

        if knowledge_targets:
            routes.append("knowledge")
            retrieval_failed = False
            for knowledge_target in knowledge_targets:
                try:
                    retrieval = await rag_service.retrieve(
                        knowledge_target,
                        user_message,
                        top_k=5 if knowledge_base_id else 3,
                    )
                    contexts.extend(
                        f"[Retrieved knowledge]\n{context}"
                        for context in retrieval["contexts"]
                    )
                    sources.extend(retrieval["sources"])
                except Exception as exc:
                    retrieval_failed = True
                    logger.warning(
                        "Knowledge retrieval failed for collection %s: %s",
                        knowledge_target,
                        exc,
                    )
            if not contexts and not retrieval_failed:
                warnings.append("No relevant passages were found in local knowledge.")
            if retrieval_failed:
                warnings.append(
                    "Some local knowledge could not be searched. Direct conversation can continue."
                )

        if _explicit_code_request(user_message):
            code = _python_block(user_message)
            if code:
                routes.append("run_code_sandbox")
                try:
                    execution = await asyncio.to_thread(
                        sandbox_service.execute,
                        CodeExecutionRequest(
                            code=code,
                            language="python",
                            conversation_id=conversation_id,
                        ),
                    )
                    result_text = (
                        f"Python sandbox execution completed with status {execution.status} "
                        f"and exit code {execution.exit_code}.\n"
                        f"STDOUT:\n{execution.stdout or '(empty)'}\n"
                        f"STDERR:\n{execution.stderr or '(empty)'}"
                    )
                    contexts.append(f"[Verified tool result]\n{result_text}")
                    yield {
                        "type": "tool",
                        "tool": "run_code_sandbox",
                        "status": execution.status,
                        "result": execution.model_dump(),
                    }
                except SandboxUnavailableError as exc:
                    warnings.append(str(exc))
                    contexts.append(
                        "[Tool status]\nCode was not executed because the Docker sandbox is unavailable."
                    )
            else:
                warnings.append(
                    "Code execution was requested, but no fenced Python code block was provided."
                )

        for warning in warnings:
            yield {"type": "warning", "message": warning}
        if sources:
            yield {"type": "sources", "sources": sources}

        if contexts:
            system_instruction = SYSTEM_DOCUMENT_INSTRUCTION
            context_text = _bounded_context(contexts, settings.max_context_characters)
            prompt = (
                "### VERIFIED DOCUMENT CONTEXT:\n"
                f"{context_text}\n\n"
                "### USER REQUEST:\n"
                f"{user_message}\n\n"
                "### INSTRUCTIONS FOR YOUR RESPONSE:\n"
                "- Conduct an analytical, high-quality analysis like ChatGPT or Gemini.\n"
                "- Cite exact documents and page numbers where applicable from the verified context above: [Document: filename, Page X].\n"
                "- NEVER output placeholders like '[Document: <general knowledge>, Page N/A]' or '[Document: <filename>]'.\n"
                "- When data or comparisons are present, format them in clear Markdown tables.\n"
                "- If the user asks for a summary, provide an Executive Summary, Key Highlights, and Core Findings.\n"
                "- If information is not present in the verified context, state that clearly."
            )
        else:
            system_instruction = SYSTEM_CONVERSATIONAL_INSTRUCTION
            prompt = user_message

        history: List[Dict[str, str]] = [{"role": "system", "content": system_instruction}]
        for previous in prior_messages:
            if previous["role"] in {"user", "assistant"}:
                history.append({"role": previous["role"], "content": previous["content"]})
        history.append({"role": "user", "content": prompt})

        yield {
            "type": "start",
            "conversation_id": conversation_id,
            "model": target_model,
            "route": routes or ["chat"],
        }

        sanitizer = StreamingCitationSanitizer()
        full_response = ""
        metrics: Dict[str, Any] = {}
        generation_history = history
        continuation_count = 0
        try:
            while True:
                segment_metrics: Dict[str, Any] = {}
                async for event in ollama_service.stream_chat(generation_history, target_model):
                    if event["type"] == "token":
                        sanitized_token = sanitizer.process(event["content"])
                        if sanitized_token:
                            full_response += sanitized_token
                            yield {"type": "token", "content": sanitized_token}
                    elif event["type"] == "metrics":
                        segment_metrics = event
                flushed = sanitizer.flush()
                if flushed:
                    full_response += flushed
                    yield {"type": "token", "content": flushed}
                metrics = segment_metrics
                if segment_metrics.get("done_reason") != "length":
                    break
                if continuation_count >= 1:
                    raise OllamaError(
                        "The answer reached the generation limit before it was complete. "
                        "Please ask for a shorter answer or split the request into sections."
                    )
                continuation_count += 1
                generation_history = [
                    *history,
                    {"role": "assistant", "content": full_response},
                    {
                        "role": "user",
                        "content": (
                            "Continue exactly where the previous response stopped. "
                            "Do not repeat completed text; finish the requested answer completely."
                        ),
                    },
                ]
        except asyncio.CancelledError:
            if full_response:
                saved_text = clean_unwanted_citations(full_response).strip()
                await asyncio.to_thread(
                    conversation_service.add_message,
                    conversation_id,
                    "assistant",
                    saved_text,
                    target_model,
                    sources,
                    {"stopped": True},
                )
            raise
        except OllamaError:
            if full_response:
                saved_text = clean_unwanted_citations(full_response).strip()
                await asyncio.to_thread(
                    conversation_service.add_message,
                    conversation_id,
                    "assistant",
                    saved_text,
                    target_model,
                    sources,
                    {"route": routes or ["chat"], "incomplete": True},
                )
            raise

        full_response = clean_unwanted_citations(full_response).strip()
        if not full_response:
            raise OllamaError("The local model completed without returning visible text.")
        assistant = await asyncio.to_thread(
            conversation_service.add_message,
            conversation_id,
            "assistant",
            full_response,
            target_model,
            sources,
            {
                "route": routes or ["chat"],
                "metrics": metrics,
                "continuations": continuation_count,
            },
        )
        yield {
            "type": "done",
            "conversation_id": conversation_id,
            "message_id": assistant["id"],
            "model": target_model,
        }


unified_ai_service = UnifiedAIService()
