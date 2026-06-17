# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.5.0 · **Last updated:** June 2026

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
│  │  LiteLLM → Groq API        │  │  ChromaDB (vector_store) │  │
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
│   └── model_registry.py   # Groq allowlist + scores
├── routers/
│   ├── auth.py
│   ├── chat.py             # /chat, /chat/stream, /chat/regenerate
│   ├── conversations.py
│   ├── model_settings.py
│   ├── user_preferences.py
│   ├── documents.py        # upload, list, search, delete
│   ├── user_api_keys.py    # CRUD + test
│   └── logs.py             # activity log queries
├── services/
│   ├── chat_service.py     # Full pipeline orchestration
│   ├── rag_service.py      # Retrieve + inject document context
│   ├── vector_store.py     # ChromaDB wrapper
│   ├── document_processor.py
│   ├── api_key_service.py
│   ├── activity_log_service.py
│   ├── model_clients.py    # LiteLLM + key resolution
│   ├── llm_classifier.py
│   ├── prompt_intelligence.py
│   ├── model_scorer.py
│   └── ...
└── tests/                  # 59 tests
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
route()                  ← model_scorer + allowlist
    │
    ▼
generate / stream        ← model_clients (user key → env key → mock)
    │
    ▼
persist + analytics + activity log
```

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
| App keys | `.env` (`GROQ_API_KEY`) | Fallback; classifier/enhancer/title |
| Mock | `ALLOW_MOCK_LLM=true` | Local demos without keys |

Resolution order in `model_clients.resolve_api_key()`: user → env → mock.

---

## Activity Logs

`activity_log_service` records structured events:

- Chat pipeline steps (classify, enhance, RAG, route, model call)
- Document upload/delete
- API key CRUD
- Login

Metadata is sanitized (no raw API keys). Endpoints: `GET /logs/my`, `GET /logs/conversation/{id}`, `GET /logs/admin/logs`.

---

## Frontend Structure

```
frontend/src/
├── App.jsx                 # Tab navigation
├── components/
│   ├── ChatPage.jsx        # Streaming + routing + RAG badges
│   ├── DocumentsPage.jsx   # Upload/list/delete
│   ├── LogsPage.jsx        # Activity log viewer
│   ├── ModelControls.jsx   # Toggles + ApiKeysSection
│   └── ...
└── api/
    ├── chat.js             # streamChat() via fetch + ReadableStream
    ├── documents.js
    └── ...
```

---

## Streaming (SSE)

`POST /chat/stream` returns `text/event-stream`:

| Event | Payload |
|-------|---------|
| `routing_start` | — |
| `routing_complete` | task, model, scores, RAG metadata |
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
| `model_runs` | Routing metadata, costs, enhanced prompt |
| `uploaded_documents` | RAG file metadata |
| `user_api_keys` | Encrypted provider keys |
| `activity_logs` | Timestamped events |

---

## External Dependencies

| Service | Usage |
|---------|-------|
| Groq API | LLM inference (chat, classify, enhance, title) |
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
