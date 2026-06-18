# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.6.0 · **Last updated:** June 2026

---

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                        │
│  Chat │ Analytics │ Documents │ Logs │ Model Controls │ Admin   │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST + SSE
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │   Auth   │ │   Chat   │ │ Documents│ │ User API Keys    │   │
│  │  (JWT)   │ │ + Stream │ │  + RAG   │ │ + Activity Logs  │   │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └──────────────────┘   │
│                    │            │                                 │
│  ┌─────────────────▼────────────▼─────────────────────────┐   │
│  │              Chat Pipeline (chat_service)                 │   │
│  │  classify → enhance → RAG retrieve → route → respond     │   │
│  └─────────────────┬────────────────────────────────────────┘   │
│                    │                                              │
│  ┌─────────────────▼──────────┐  ┌──────────────────────────┐  │
│  │  LiteLLM → Groq / OpenAI   │  │  ChromaDB (vector_store) │  │
│  │           / Anthropic       │  │                          │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SQLite — users, conversations, messages, model_runs,     │   │
│  │  uploaded_documents, user_api_keys, activity_logs           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Structure

```
backend/
├── main.py                 # FastAPI app, CORS, routers
├── database.py             # SQLAlchemy models
├── config/
│   ├── model_registry.py   # Multi-provider allowlist + scores
│   └── models.yaml         # Task profiles and scoring weights
├── routers/
│   ├── auth.py
│   ├── chat.py             # /chat, /chat/stream, /chat/regenerate
│   ├── conversations.py
│   ├── analytics.py        # summary, history, model-usage, provider-usage
│   ├── model_settings.py
│   ├── user_preferences.py
│   ├── documents.py        # upload, list, search, delete
│   ├── user_api_keys.py    # CRUD + test
│   ├── logs.py             # GET /logs/my, /logs/conversation/{id}
│   └── admin.py            # employee-usage, user-metrics, /admin/logs
├── services/
│   ├── chat_service.py     # Full pipeline orchestration
│   ├── router_engine.py    # Score enabled models, pick best
│   ├── rag_service.py      # Retrieve + inject document context
│   ├── vector_store.py     # ChromaDB wrapper
│   ├── document_processor.py
│   ├── api_key_service.py
│   ├── activity_logger.py
│   ├── model_clients.py    # LiteLLM + per-provider key resolution
│   ├── groq_models.py      # Model catalog sync
│   ├── llm_classifier.py
│   ├── prompt_intelligence.py
│   ├── model_scorer.py
│   ├── report_generator.py
│   └── ...
└── tests/                  # 85 tests
```

---

## Chat Pipeline

```
User message
    │
    ▼
build_context()          ← conversation history
    │
    ▼
classify_task()          ← llm_classifier (Groq) or keyword fallback
    │
    ▼
analyze_and_enhance()    ← prompt_intelligence v2 (if enabled)
    │
    ▼
retrieve_rag_context()   ← ChromaDB top-3 chunks (rag_service)
    │
    ▼
route()                  ← router_engine + model_scorer (provider-key filter)
    │
    ▼
generate / stream        ← model_clients (user key → env key → mock)
    │
    ▼
persist + analytics + activity log
```

---

## Model Catalog

| Provider | Chat models | Notes |
|----------|-------------|-------|
| Groq | 6 models | Synced against live Groq API when `GROQ_API_KEY` set |
| OpenAI | gpt-4o-mini, gpt-4o, o3-mini | Registry metadata only |
| Anthropic | claude-3-5-sonnet, claude-3-haiku | Registry metadata only |
| Audio | whisper-large-v3 | Cataloged; not chat-routable |

`MODEL_ALLOWLIST` in `model_registry.py` is the source of truth. `CHAT_MODEL_IDS` excludes whisper.

---

## RAG Architecture

| Component | Role |
|-----------|------|
| `document_processor.py` | Parse TXT/MD/PDF; split into chunks |
| `vector_store.py` | Embed with `all-MiniLM-L6-v2`; store in ChromaDB |
| `uploaded_documents` table | Metadata (filename, user_id, chunk count) |
| `rag_service.py` | Search by user message; filter by threshold; format context |
| Chat injection | Prepended to system prompt before LLM call |

Env: `CHROMA_PERSIST_DIR`, `RAG_SIMILARITY_THRESHOLD` (default 0.4).

---

## API Key Architecture

| Layer | Storage | Usage |
|-------|---------|-------|
| User keys | `user_api_keys` table, Fernet-encrypted | Chat + regenerate (per provider) |
| App keys | `.env` per provider | Fallback; classifier/enhancer/title (Groq only) |
| Mock | `ALLOW_MOCK_LLM=true` | Local demos without keys |

Supported providers: `groq`, `openai`, `anthropic`, `google`, `bedrock` (placeholder).

Resolution order in `model_clients`: user key → env key → mock (per provider).

Routing in `model_scorer.filter_candidates_by_provider_keys()` keeps only models whose provider has a key. If no provider has keys, all candidates remain (mock mode).

---

## Activity Logs

`activity_logger.py` records structured events:

- Chat pipeline steps (classify, enhance, RAG, route, model call)
- Document upload/delete
- API key CRUD
- Login

Metadata is sanitized (no raw API keys). Endpoints: `GET /logs/my`, `GET /logs/conversation/{id}`, `GET /admin/logs`.

---

## Frontend Structure

```
frontend/src/
├── App.jsx                 # Tab navigation
├── components/
│   ├── ChatPage.jsx        # Streaming + routing + provider/RAG badges
│   ├── DocumentsPage.jsx   # Upload/list/delete
│   ├── LogsPage.jsx        # Activity log viewer
│   ├── AnalyticsDashboard.jsx  # KPIs + model/provider tables
│   ├── ModelControls.jsx   # Toggles + ApiKeysSection
│   └── ...
└── api/
    ├── chat.js             # streamChat() via fetch + ReadableStream
    ├── analytics.js        # summary, model-usage, provider-usage
    ├── documents.js
    └── apiKeys.js
```

---

## Streaming (SSE)

`POST /chat/stream` returns `text/event-stream`:

| Event | Payload |
|-------|---------|
| `routing_start` | — |
| `routing_complete` | task, model, provider, scores, provider_availability, RAG metadata |
| `token` | `{ "content": "..." }` |
| `complete` | full message + analytics + RAG fields |
| `error` | error message |

Frontend default: `streamChat()` in `api/chat.js`.

---

## Data Model (key tables)

| Table | Purpose |
|-------|---------|
| `users` | Auth, role (user/admin) |
| `conversations` | Per-user threads |
| `messages` | User + assistant content |
| `model_runs` | Routing metadata, provider, costs, enhanced prompt |
| `uploaded_documents` | RAG file metadata |
| `user_api_keys` | Encrypted provider keys |
| `activity_logs` | Timestamped events |

---

## External Dependencies

| Service | Usage |
|---------|-------|
| Groq API | LLM inference, classify, enhance, title; Groq model sync |
| OpenAI API | gpt-4o-mini, gpt-4o, o3-mini inference |
| Anthropic API | Claude inference |
| ChromaDB | Local vector persistence |
| sentence-transformers | Document + query embeddings |

---

## Deployment Topology

| Service | Host | Notes |
|---------|------|-------|
| API | Render | `render.yaml` blueprint; `/health` check |
| Frontend | Vercel | `VITE_API_BASE` at build time |
| SQLite | Render disk (optional) | `/var/data` for persistence |
| ChromaDB | Render disk (optional) | Set `CHROMA_PERSIST_DIR` on mounted path |

See [deploy-render.md](deploy-render.md) and [deploy-vercel.md](deploy-vercel.md).
