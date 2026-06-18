# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.6.0 · **Last updated:** June 2026

---

## What TokenMaxx Is

TokenMaxx is a **cost-optimized multi-provider LLM routing platform** for teams. It classifies each prompt, enhances it with Prompt Intelligence v2, optionally retrieves context from uploaded documents (RAG), routes to the best allowed model across Groq, OpenAI, and Anthropic, streams the answer live, and tracks savings vs. a GPT-4o baseline.

**Stack:** FastAPI + SQLite + ChromaDB + React/Vite + LiteLLM (multi-provider) + JWT auth.

---

## Current State (v0.6.0)

| Area | Status |
|------|--------|
| Auth | JWT login/signup; bcrypt passwords |
| Multi-provider routing | 11 chat models (Groq, OpenAI, Anthropic); provider-key filtering |
| Chat | Sync `POST /chat` + **SSE** `POST /chat/stream` (default UI) |
| RAG | Document upload (TXT/MD/PDF), ChromaDB search, chat context injection |
| Documents UI | Upload, list, delete in **Documents** tab |
| Prompt Intelligence v2 | Analyze + enhance; complexity 0–100; clean prompts |
| Routing | LLM classifier + keyword fallback; task-aware scoring with premium bonuses |
| Model Controls | Admin org-wide + user personal toggles; **API Keys** (5 providers) |
| Activity Logs | Backend event log; **Logs** tab (admin sees all via `/admin/logs`) |
| Regenerate | One LLM call per model chip (non-streaming) |
| Analytics | KPIs + model/provider breakdown + CSV export |
| Admin | Employee usage dashboard |
| Tests | **85** pytest tests |
| Deploy | Render (backend) + Vercel (frontend) guides in `docs/` |

---

## App Tabs

| Tab | Purpose |
|-----|---------|
| Chat | Streaming chat, routing panel, provider badges, RAG badges |
| Analytics | Usage KPIs, model/provider breakdown, CSV export |
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
| `model_scorer.py` | Complexity-aware routing scores; provider-key filtering |
| `model_registry.py` | Multi-provider allowlist + editorial scores |
| `groq_models.py` | Model catalog sync (Groq API + registry metadata) |
| `router_engine.py` | Score enabled models and pick best fit |
| `model_clients.py` | LiteLLM generate/stream; per-provider API key resolution |
| `chat_service.py` | Full chat pipeline (classify → enhance → RAG → route → respond) |
| `rag_service.py` | Retrieve top chunks, inject into system prompt |
| `vector_store.py` | ChromaDB persistence + similarity search |
| `document_processor.py` | Chunk TXT/MD/PDF for embedding |
| `api_key_service.py` | Encrypted per-user provider keys |
| `activity_logger.py` | Structured event logging with metadata redaction |
| `key_encryption.py` | Fernet encrypt/decrypt user API keys |
| `report_generator.py` | Analytics summary, model usage, provider usage |

---

## API Key Resolution (chat + regenerate)

Per provider:

1. User's stored key for that provider (if set and active)
2. App-level env key (`GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`)
3. Mock response if `ALLOW_MOCK_LLM=true` (default locally)

Classifier, enhancer, title, and Groq model sync still use app `.env` keys only (Groq).

Routing filters candidates to providers with configured keys. If no provider has keys, all candidates remain eligible (mock fallback).

---

## RAG Pipeline

1. User uploads document → chunked → embedded → stored in ChromaDB + metadata in SQLite
2. On chat turn: after `build_context()`, `rag_service` searches user's docs
3. Top 3 chunks above `RAG_SIMILARITY_THRESHOLD` (default 0.4) injected into system prompt
4. Response includes `rag_used`, `retrieved_chunk_count`, `source_filenames`

---

## LLM Touchpoints

| Step | When | Model / store | Key source |
|------|------|---------------|------------|
| Classify | Each chat turn | `llm_classifier` → llama-3.1-8b-instant | App `GROQ_API_KEY` |
| Analyze + enhance | Each turn (if enabled) | Prompt Intelligence v2 | App `GROQ_API_KEY` |
| RAG embed/search | Upload + each chat turn | sentence-transformers + ChromaDB | N/A |
| Route + respond | Each chat turn | Scored allowlisted model (any provider) | User key → env → mock |
| Title | First turn | `auxiliary.title` | App `GROQ_API_KEY` |
| Regenerate | User click only | User-selected model (sync) | User key → env → mock |

---

## Environment Variables

See `backend/.env.example`. Notable vars:

- `GROQ_API_KEY` — Groq inference + auxiliary LLM steps
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` — multi-provider routing
- `CHROMA_PERSIST_DIR` — vector store path
- `RAG_SIMILARITY_THRESHOLD` — min similarity for chat RAG
- `API_KEY_ENCRYPTION_SECRET` — encrypt user keys at rest
- `ALLOW_MOCK_LLM` — mock when no key (default `true` locally)

---

## Tests

```bash
cd backend && pytest -v
```

85 tests across auth, chat, streaming, routing, provider routing, premium routing, classifier, prompt intelligence, documents, RAG, API keys, activity logs, and analytics.

---

## Deployment

- **Backend:** Render — see [deploy-render.md](deploy-render.md)
- **Frontend:** Vercel — see [deploy-vercel.md](deploy-vercel.md)
- Cross-link: `VITE_API_BASE` ↔ `CORS_ORIGINS`

---

## Repo

https://github.com/Apatel468/TokenMaxx
