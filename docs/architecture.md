# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.7.0 · **Last updated:** June 2026

---

## High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                             │
│  Chat (sentiment + routing panels) │ Analytics │ Documents │ Logs    │
│  Model Controls │ Admin                                              │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ REST + SSE
┌────────────────────────────▼─────────────────────────────────────────┐
│                     FastAPI Backend                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐   │
│  │   Auth   │ │   Chat   │ │ Documents│ │ Sentiment + Provider │   │
│  │  (JWT)   │ │ + Stream │ │  + RAG   │ │ Settings + Generation│   │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └──────────────────────┘   │
│                    │            │                                     │
│  ┌─────────────────▼────────────▼──────────────────────────────┐   │
│  │              Chat Pipeline (chat_service)                      │   │
│  │  classify → intent → enhance → RAG → route → respond/generate  │   │
│  └─────────────────┬──────────────────────────────────────────────┘   │
│                    │                                                  │
│  ┌─────────────────▼──────────┐  ┌──────────────────────────┐       │
│  │  LiteLLM → Groq / OpenAI   │  │  ChromaDB (vector_store) │       │
│  │           / Anthropic       │  │                          │       │
│  └────────────────────────────┘  └──────────────────────────┘       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  SQLite — users, conversations, messages, model_runs,           │   │
│  │  provider_settings, message_sentiments, generated_documents,    │   │
│  │  uploaded_documents, user_api_keys, activity_logs               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Backend Structure

```
backend/
├── main.py                 # FastAPI app, CORS, routers (v0.7.0)
├── database.py             # SQLAlchemy models + migrations
├── config/
│   ├── model_registry.py   # Multi-provider allowlist + scores
│   └── models.yaml         # Task profiles and scoring weights
├── routers/
│   ├── auth.py
│   ├── chat.py             # /chat, /chat/stream, /chat/regenerate
│   ├── conversations.py
│   ├── analytics.py
│   ├── model_settings_route.py   # GET/PUT /model-settings
│   ├── provider_settings.py    # GET/PUT /provider-settings
│   ├── sentiment.py            # POST /sentiment/analyze, history
│   ├── generations.py          # download, preview, history
│   ├── documents.py
│   ├── user_api_keys.py
│   ├── logs.py
│   └── admin.py
├── services/
│   ├── chat_service.py
│   ├── router_engine.py
│   ├── model_settings.py       # Model + provider availability
│   ├── generation/             # intent, document_writer, image_generator
│   ├── generation_service.py
│   ├── sentiment_analyzer.py
│   ├── sentiment_service.py
│   ├── rag_service.py
│   ├── vector_store.py
│   ├── model_clients.py
│   └── ...
└── tests/                  # 118 tests
```

---

## Chat Pipeline

```
User message
    │
    ├─► POST /sentiment/analyze (async, parallel — UI only)
    │
    ▼
build_context()          ← conversation history
    │
    ▼
classify_task()          ← llm_classifier or keyword fallback
    │
    ▼
detect_generation_intent()  ← chat | document | image
    │
    ├─ document/image → generation_service (skip token stream)
    │
    ▼
analyze_and_enhance()    ← prompt_intelligence v2 (if enabled)
    │
    ▼
retrieve_rag_context()   ← ChromaDB top-3 chunks
    │
    ▼
route()                  ← enabled models (provider + admin + user)
    │
    ▼
generate / stream        ← model_clients
    │
    ▼
persist + analytics + activity log + sentiment store
```

---

## Model Availability

```
enabled = provider_enabled AND admin_enabled AND user_enabled
```

`get_enabled_model_ids()` in `model_settings.py` gates `router_engine.route()`.

---

## Model Catalog

| Provider | Chat models | Notes |
|----------|-------------|-------|
| Groq | 6 models | Synced against live Groq API when `GROQ_API_KEY` set |
| OpenAI | gpt-4o-mini, gpt-4o, o3-mini | Registry metadata |
| Anthropic | claude-3-5-sonnet, claude-3-haiku | Registry metadata |
| Audio | whisper-large-v3 | Cataloged; not chat-routable |

---

## Frontend Structure

```
frontend/src/
├── App.jsx
├── components/
│   ├── ChatPage.jsx        # 3-column: sidebar | thread | sentiment + routing
│   ├── SentimentPanel.jsx  # Real-time sentiment + trend
│   ├── ModelControls.jsx   # Provider toggles + grouped models
│   ├── AnalyticsDashboard.jsx
│   ├── attachments/        # Generated file/image renderers
│   └── ...
└── api/
    ├── chat.js             # streamChat() SSE
    ├── sentiment.js
    ├── settings.js         # model-settings + provider-settings
    └── generations.js
```

---

## Streaming (SSE)

`POST /chat/stream` events: `routing_start`, `routing_complete`, `token`, `generation_*`, `artifact`, `complete`, `error`.

---

## Data Model (key tables)

| Table | Purpose |
|-------|---------|
| `users` | Auth, role (user/admin) |
| `conversations` | Per-user threads |
| `messages` | User + assistant content; generation artifact refs |
| `model_runs` | Routing metadata, provider, costs |
| `provider_settings` | Org-wide provider enable/disable |
| `admin_model_settings` | Per-model org toggles |
| `user_model_settings` | Per-user model preferences |
| `message_sentiments` | Per-user-message tone analysis |
| `generated_documents` / `generated_images` | Generation artifacts |
| `uploaded_documents` | RAG file metadata |
| `user_api_keys` | Encrypted provider keys |
| `activity_logs` | Timestamped events |

---

## Deployment Topology

| Service | Host | Notes |
|---------|------|-------|
| API | Render | `render.yaml`; `/health` check |
| Frontend | Vercel | `VITE_API_BASE` at build time |
| SQLite | Render disk (optional) | `/var/data` |
| ChromaDB + generated files | Render disk (optional) | `CHROMA_PERSIST_DIR`, `GENERATED_FILES_DIR` |

See [deploy-render.md](deploy-render.md) and [deploy-vercel.md](deploy-vercel.md).
