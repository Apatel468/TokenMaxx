# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.5.0 · **Last updated:** June 2026

---

## What TokenMaxx Is

TokenMaxx is a **cost-optimized LLM routing platform** for teams. It classifies each prompt, enhances it with Prompt Intelligence v2, optionally retrieves context from uploaded documents (RAG), routes to the best allowed Groq model, streams the answer live, and tracks savings vs. a GPT-4o baseline.

**Stack:** FastAPI + SQLite + ChromaDB + React/Vite + LiteLLM (Groq) + JWT auth.

---

## Current State (v0.5.0)

| Area | Status |
|------|--------|
| Auth | JWT login/signup; bcrypt passwords |
| Chat | Sync `POST /chat` + **SSE** `POST /chat/stream` (default UI) |
| RAG | Document upload (TXT/MD/PDF), ChromaDB search, chat context injection |
| Documents UI | Upload, list, delete in **Documents** tab |
| Prompt Intelligence v2 | Analyze + enhance; complexity 0–100; clean prompts |
| Routing | LLM classifier + keyword fallback; task-aware scoring |
| Model Controls | Admin org-wide + user personal toggles; **API Keys** section |
| Activity Logs | Backend event log; **Logs** tab (admin sees all) |
| Regenerate | One LLM call per model chip (non-streaming) |
| Analytics | In-memory KPIs + CSV export |
| Admin | Employee usage dashboard |
| Tests | **59** pytest tests |
| Deploy | Render (backend) + Vercel (frontend) guides in `docs/` |

---

## App Tabs

| Tab | Purpose |
|-----|---------|
| Chat | Streaming chat, routing panel, RAG badges |
| Analytics | Usage KPIs, model breakdown, CSV export |
| Documents | Upload/manage RAG source files |
| Logs | Activity log viewer |
| Model Controls | Model toggles, prompt enhancement, API keys |
| Admin | Employee usage (admins only) |

---

## Key Backend Modules

| Module | Role |
|--------|------|
| `llm_classifier.py` | Groq task classification |
| `prompt_intelligence.py` | Analyze + enhance prompts (v2) |
| `model_scorer.py` | Complexity-aware routing scores |
| `model_registry.py` | Groq allowlist + editorial scores |
| `model_clients.py` | LiteLLM generate/stream; API key resolution |
| `chat_service.py` | Full chat pipeline (classify → enhance → RAG → route → respond) |
| `rag_service.py` | Retrieve top chunks, inject into system prompt |
| `vector_store.py` | ChromaDB persistence + similarity search |
| `document_processor.py` | Chunk TXT/MD/PDF for embedding |
| `api_key_service.py` | Encrypted per-user provider keys |
| `activity_log_service.py` | Structured event logging |
| `key_encryption.py` | Fernet encrypt/decrypt user API keys |

---

## API Key Resolution (chat + regenerate)

1. User's stored key for the provider (if set and enabled)
2. App-level `GROQ_API_KEY` from `.env`
3. Mock response if `ALLOW_MOCK_LLM=true` (default locally)

Classifier, enhancer, title, and Groq model sync still use app `.env` keys only.

---

## RAG Pipeline

1. User uploads document → chunked → embedded → stored in ChromaDB + metadata in SQLite
2. On chat turn: after `build_context()`, `rag_service` searches user's docs
3. Top 3 chunks above `RAG_SIMILARITY_THRESHOLD` (default 0.4) injected into system prompt
4. Response includes `rag_used`, `retrieved_chunk_count`, `source_filenames`

---

## Groq Touchpoints

| Step | When | Model / store |
|------|------|---------------|
| Classify | Each chat turn | `llm_classifier` → llama-3.1-8b-instant |
| Analyze + enhance | Each turn (if enabled) | Prompt Intelligence v2 |
| RAG embed/search | Upload + each chat turn | sentence-transformers + ChromaDB |
| Route + respond | Each chat turn | Scored allowlisted model (stream or sync) |
| Title | First turn | `auxiliary.title` |
| Regenerate | User click only | User-selected model (sync) |

---

## Environment Variables

See `backend/.env.example`. Notable additions in v0.5.0:

- `CHROMA_PERSIST_DIR` — vector store path
- `RAG_SIMILARITY_THRESHOLD` — min similarity for chat RAG
- `API_KEY_ENCRYPTION_SECRET` — encrypt user keys at rest
- `ALLOW_MOCK_LLM` — mock when no key (default `true` locally)

---

## Tests

```bash
cd backend && pytest -v
```

59 tests across auth, chat, streaming, routing, classifier, prompt intelligence, documents, RAG, API keys, and activity logs.

---

## Deployment

- **Backend:** Render — see [deploy-render.md](deploy-render.md)
- **Frontend:** Vercel — see [deploy-vercel.md](deploy-vercel.md)
- Cross-link: `VITE_API_BASE` ↔ `CORS_ORIGINS`

---

## Repo

https://github.com/Apatel468/TokenMaxx
