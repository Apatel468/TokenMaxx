# TokenMaxx — Architectural Decisions

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.6.0 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Backend | FastAPI | OpenAPI, Pydantic, `StreamingResponse` for SSE |
| Database | SQLite | Zero setup for MVP |
| Vector store | ChromaDB + sentence-transformers | Local persistence; no external vector DB for MVP |
| Auth | bcrypt + PyJWT (HS256) | Simple stateless tokens |
| LLM gateway | LiteLLM | Unified multi-provider interface + `stream=True` |
| Streaming | Server-Sent Events | `POST /chat/stream`; frontend uses fetch + ReadableStream |
| Providers | Groq, OpenAI, Anthropic (allowlisted) | Cost/speed on Groq; premium tiers when keys configured |
| Frontend | React + Vite | Fast iteration |
| Tests | pytest + httpx | 85 tests; mocked LLM/stream in CI |

---

## Architectural Decisions

### Multi-provider model allowlist (v0.6.0) 🔒
**Decision:** Only models in `MODEL_ALLOWLIST` are synced, routed, and shown in Model Controls.  
**Chat:** 11 models across Groq (6), OpenAI (3), Anthropic (2). **Audio:** `whisper-large-v3` only (not chat-routable).  
**Routing:** Candidates filtered to providers with user or app API keys via `filter_candidates_by_provider_keys()`.  
**Why:** Premium models for business/coding when warranted; economy Groq models for simple tasks.

### Groq model allowlist (v0.3.2) 🔒
**Decision:** `GROQ_MODEL_ALLOWLIST` is a subset of `MODEL_ALLOWLIST`. Groq-hosted models optionally synced against live Groq API.  
**Superseded by:** Multi-provider allowlist (v0.6.0) — `GROQ_MODEL_ALLOWLIST` remains for Groq sync scope.

### SSE streaming chat (v0.4.0) 🔒
**Decision:** `POST /chat/stream` returns `text/event-stream` with events: `routing_start`, `routing_complete`, `token`, `complete`, `error`.  
**Frontend default:** `streamChat()` in `api/chat.js`; `POST /chat` kept for sync/tests.  
**Persistence:** Assistant message saved only after stream completes.  
**Fallback:** Word-by-word fake stream when provider streaming unavailable.  
**Why:** Live token display for demos; routing metadata arrives before tokens.

### Prompt Intelligence Engine v2 (v0.4.0) 🔒
**Decision:** `prompt_intelligence.py` analyzes then enhances — not just rewrite.  
**Outputs:** `PromptAnalysis` with task_type, complexity_score (0–100), complexity_level, persona, output_format, enhancement_strategy, enhanced_prompt.  
**Complexity tiers:** simple → minimal; medium → structured; complex → full specification.  
**Clean prompts:** No `[Original user request — preserve this intent: ...]` in stored or displayed text.  
**Why:** Task- and complexity-aware enhancement; transparent metadata for demos.

### RAG with ChromaDB (v0.5.0) 🔒
**Decision:** Per-user document collections in ChromaDB; metadata in SQLite `uploaded_documents`.  
**Pipeline:** After `build_context()` and before `route()` in `chat_service.prepare_chat_turn()`.  
**Retrieval:** Top 3 chunks; cosine similarity threshold 0.4 (`RAG_SIMILARITY_THRESHOLD`).  
**Injection:** Retrieved text prepended to system prompt via `rag_service.py`.  
**Formats:** TXT, MD, PDF.  
**Why:** Ground answers in user uploads without external vector DB cost.

### User API keys (v0.5.0) 🔒
**Decision:** Users can store per-provider keys encrypted with Fernet (`API_KEY_ENCRYPTION_SECRET`).  
**Supported providers:** groq, openai, anthropic, google, bedrock (placeholder).  
**Resolution order (chat + regenerate):** user key → app env key → mock if `ALLOW_MOCK_LLM=true`.  
**Not used for:** classifier, enhancer, title, Groq model sync (app `.env` Groq key only).  
**Why:** BYOK for power users; app keys as fallback for demos.

### Activity logs (v0.5.0)
**Decision:** Structured events in `activity_logs` via `activity_logger.py`; metadata sanitized (no raw keys).  
**Scope:** Chat pipeline, RAG, routing, model calls, login, document upload, API key CRUD.  
**Access:** Users see own logs; admins see all via `GET /admin/logs`.  
**Why:** Debuggability and demo transparency without log aggregation infra.

### LLM task classifier (v0.3.3) 🔒
**Decision:** `llm_classifier.py` + keyword fallback in `prompt_analyzer.py`.  
**Note:** Classifier task types (routing) differ from enhancement task types (v2 normalization).

### Task-aware routing (v0.3.3) 🔒
**Decision:** Complexity-aware dynamic weights + `TASK_MODEL_BONUSES` in `model_scorer.py`.  
**v0.6.0 extension:** Bonuses include OpenAI and Anthropic models for business, coding, and reasoning tasks.

### Client-side analytics export (v0.3.3)
**Decision:** `tokenmaxx-analytics-report.csv` from Analytics tab data; no dedicated export endpoint.

### On-demand model regenerate (v0.3.2) 🔒
**Decision:** One LLM call per chip click; reuses stored prompts; **non-streaming**.

### Optional prompt enhancement (v0.3.2)
**Decision:** User toggle `enhance_prompts`; when off, `build_disabled_analysis()` skips enhancer Groq call.

### Two-tier model enable/disable (v0.3.1) 🔒
**Rule:** `available = admin_enabled AND user_enabled`

### Original prompt preserved in DB 🔒
User `messages.content` = original text; `model_runs.enhanced_prompt` = clean enhanced text sent to model.

---

## LLM Touchpoints (with API key)

| Step | When | Model | Key source |
|------|------|-------|------------|
| Classify | Each chat turn | `llm_classifier` → llama-3.1-8b-instant | App `GROQ_API_KEY` |
| Analyze + enhance | Each turn (if enabled) | Prompt Intelligence v2 | App `GROQ_API_KEY` |
| RAG embed/search | Upload + each chat turn | sentence-transformers + ChromaDB | N/A |
| Route + respond | Each chat turn | Scored allowlisted model (any provider) | User key → env → mock |
| Title | First turn | `auxiliary.title` | App `GROQ_API_KEY` |
| Regenerate | User click only | User-selected model (sync) | User key → env → mock |

---

## Registry Score Caveat

Scores in `model_registry.py` are editorial estimates. Routing uses `model_scorer.py` bonuses; enhancement uses `prompt_intelligence.py` personas and strategies.
