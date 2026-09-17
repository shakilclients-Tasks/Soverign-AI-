# Sovereign AI

Private, on-premise conversational AI for local models, documents, knowledge retrieval, and explicitly authorized tools.

Sovereign AI has one user experience: a single streaming chat. React communicates only with FastAPI; FastAPI selects the required local capability and communicates with Ollama, SQLite, ChromaDB, document extraction, OCR, or the Docker sandbox.

## Architecture

```text
React + Vite + TypeScript
           |
           v
       FastAPI
           |
           v
  UnifiedAIService
    |      |       |
  Ollama  RAG   local tools
           |
   ChromaDB + SQLite
```

The runtime discovers installed Ollama models from `/api/tags`. Generation models and embedding-only models are classified separately, and an embedding model can never be selected for chat.

## Requirements

- Python 3.11+
- Node.js 20+
- Ollama bound to `127.0.0.1:11434`
- At least one Ollama chat model
- An embedding model such as `nomic-embed-text` for knowledge search
- RapidOCR and ONNX Runtime from `requirements.txt` for scanned documents and images
- Docker for isolated Python execution (execution remains disabled without it)

Local models are the default. Optional Ollama `:cloud` models can be registered and selected
explicitly; when selected, prompts and extracted attachment text leave the device through the
signed-in Ollama account.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Set-Location frontend
npm install
Set-Location ..
Copy-Item .env.example .env
```

Leave `SOVEREIGN_CHAT_MODEL` empty to select the first detected compatible chat model. Set model choices safely from **Settings → AI models** after startup.

The app runs in trusted single-user mode and opens directly without a login screen. Keep FastAPI bound to loopback; there is no password or session-token gate.

For low-memory Windows machines, `sovereign-llm` is the ultra-responsive chat profile (85+ tokens/second). The higher-capacity `sovereign-doc-expert` can remain installed for extended document synthesis. The fast profile uses an 8K context, bounded responses, disabled thinking, and a one-hour model keep-alive to reduce cold starts.

OCR uses the bundled RapidOCR ONNX models and does not require a separate Windows Tesseract
installation. If Tesseract is installed, it is detected automatically as a fallback.

### Optional Ollama Cloud models

`glm-5.3-flash:cloud` is supported and appears in **Settings → AI models** after
`ollama pull glm-5.3-flash:cloud`. The interface labels cloud inference everywhere it matters.
The model requires eligible Ollama cloud usage; HTTP 401/402/403 responses are converted into a
clear subscription/access message instead of a generic generation failure. Sovereign LLM remains the
private fallback until cloud access is enabled and GLM is selected explicitly.

## Development

## Unified Single-Host Runner (Recommended)

To run everything (Frontend, Backend API, SQLite, and Ollama) seamlessly on **ONE Host Link**:

```powershell
python run.py
```

Or double-click `start.bat`. This automatically:
- Checks/starts local Ollama
- Verifies the compiled frontend bundle
- Launches FastAPI at `http://127.0.0.1:8000`
- Opens your default web browser directly to `http://127.0.0.1:8000`

## Manual Development Mode

If you prefer running components in separate terminals for active development:

```powershell
# Terminal 1: Backend
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend Dev Server (with HMR)
Set-Location frontend
npm run dev
```

## API

- `GET /api/health` — structured backend, Ollama, database, vector, and model readiness
- `GET /api/models` — detected chat and embedding inventories
- `POST /api/chat/stream` — local SSE conversation stream
- `/api/conversations` — local conversation history
- `/api/attachments` — chat-native document ingestion
- `/api/knowledge` — secondary collection and indexing management
- `/api/settings/*` — model configuration and low-priority diagnostics

## Verification

```powershell
python -m pytest -q

Set-Location frontend
npm run build
```

For a live inference check, start Ollama and FastAPI, then send `Hi` followed by `What is air-gap isolation?` in the same chat. Tokens should arrive incrementally, and refreshing the application should reload the four persisted messages from SQLite.

## Local data

Runtime state stays under `data/`:

- `data/database/sovereign.db` — users, sessions, conversations, messages, settings, and audit events
- `data/uploads/` — locally ingested documents
- `data/chroma/` — persistent vector collections

Back up these directories according to your organization’s local retention policy. Do not expose the Ollama or FastAPI ports beyond the trusted host. This build intentionally has no password checking; add an approved authentication proxy before any network exposure.
