# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.5.0 · **Last updated:** June 2026

---

## Problem

Teams want LLM quality without always paying premium-model prices. TokenMaxx automatically picks the cheapest Groq model that fits each task, enhances prompts intelligently, grounds answers in uploaded documents, and proves savings with transparent routing metadata.

---

## Core Flows

### 1. Chat (streaming)

1. User sends message in Chat tab
2. Frontend calls `POST /chat/stream` (SSE)
3. Backend: classify → enhance → **RAG retrieve** → route → stream tokens
4. UI shows routing panel, then token-by-token reply; RAG badge if documents used
5. Assistant message persisted after stream completes

### 2. Document upload (RAG)

1. User uploads TXT/MD/PDF in Documents tab
2. Backend chunks, embeds, stores in ChromaDB; metadata in SQLite
3. On next chat turn, relevant chunks injected into system prompt

### 3. Model regenerate

1. User clicks alternate model chip on assistant message
2. `POST /chat/regenerate` — one sync LLM call with stored enhanced prompt
3. Non-streaming; reuses routing context from original turn

### 4. API keys

1. User adds Groq key in Model Controls → encrypted in DB
2. Chat/regenerate use user key first; fall back to app `GROQ_API_KEY`
3. Test endpoint validates key against provider

### 5. Activity logs

1. Pipeline events written to `activity_logs` on each significant action
2. Users see own logs; admins see all via Logs tab

---

## Routing Design

| Input | Source |
|-------|--------|
| Task type | `llm_classifier` or keyword fallback |
| Complexity | `prompt_intelligence` (0–100 score) |
| Model scores | `model_registry` editorial + `model_scorer` bonuses |
| Filters | Admin disable, user disable, Groq allowlist |

Output: selected model + top-5 candidates with scores and savings %.

---

## Prompt Intelligence v2

| Field | Description |
|-------|-------------|
| `task_type` | coding, business, creative, etc. |
| `complexity_score` | 0–100 |
| `complexity_level` | simple / medium / complex |
| `persona` | Expert role for the model |
| `enhancement_strategy` | minimal / structured / full |
| `enhanced_prompt` | Clean text sent to LLM (no bracket notes) |

Toggle: `enhance_prompts` in user preferences.

---

## RAG Design

| Setting | Default |
|---------|---------|
| Top-K chunks | 3 |
| Similarity threshold | 0.4 (`RAG_SIMILARITY_THRESHOLD`) |
| Embedding model | `all-MiniLM-L6-v2` |
| Scope | Per-user document collection |

Response fields: `rag_used`, `retrieved_chunk_count`, `source_documents`, `source_filenames`.

---

## Cost Model

- **Actual cost:** LiteLLM token usage × Groq model price
- **Premium baseline:** Same tokens × GPT-4o price
- **Savings %:** `(premium - actual) / premium × 100`

Stored per `model_run` and aggregated in Analytics.

---

## Security

| Concern | Approach |
|---------|----------|
| Auth | JWT (HS256), bcrypt passwords |
| User API keys | Fernet encryption (`API_KEY_ENCRYPTION_SECRET`) |
| Activity logs | Metadata only; keys never logged |
| CORS | `CORS_ORIGINS` whitelist in production |
| Admin | Role-based access on admin routes and logs |

---

## Scalability Notes (MVP)

- SQLite + local ChromaDB suit single-instance deploy
- For multi-instance: migrate to Postgres + hosted vector DB
- SSE requires sticky sessions or stateless stream design for horizontal scale

---

## Test Coverage

59 pytest tests:

- Auth, conversations, health
- Chat sync + stream
- Routing, classifier, prompt intelligence
- Documents + RAG in chat
- API keys + activity logs
- Model settings

LLM calls mocked in CI via `ALLOW_MOCK_LLM` and test fixtures.
