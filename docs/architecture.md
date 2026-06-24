# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.8.0 · **Last updated:** June 2026

---

## High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                             │
│  Chat (sentiment + routing + web research) │ Analytics │ Documents   │
│  Logs │ Model Controls │ Admin                                        │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ REST + SSE
┌────────────────────────────▼─────────────────────────────────────────┐
│                     FastAPI Backend (v0.8.0)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐   │
│  │   Auth   │ │   Chat   │ │ Documents│ │ Sentiment + Web      │   │
│  │  (JWT)   │ │ + Stream │ │  + RAG   │ │ Research + Generation│   │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └──────────────────────┘   │
│                    │            │                                     │
│  ┌─────────────────▼────────────▼──────────────────────────────┐   │
│  │              Chat Pipeline (chat_service)                      │   │
│  │  classify → enhance → RAG → web research → sentiment → route   │   │
│  └─────────────────┬──────────────────────────────────────────────┘   │
│                    │                                                  │
│  ┌─────────────────▼──────────┐  ┌────────────┐  ┌──────────────┐   │
│  │  LiteLLM → Groq/OpenAI/    │  │  ChromaDB  │  │ Tavily/Serper│   │
│  │           Anthropic          │  │  (RAG)     │  │ + web scraper│   │
│  └────────────────────────────┘  └────────────┘  └──────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  SQLite — users, conversations, messages, model_runs,           │   │
│  │  provider_settings, message_sentiments, web research metadata,  │   │
│  │  generated_documents, uploaded_documents, activity_logs         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Backend Structure

```
backend/
├── main.py                 # FastAPI app, CORS, routers (v0.8.0)
├── database.py             # SQLAlchemy models + migrations
├── config/
│   ├── model_registry.py   # Multi-provider allowlist + scores
│   └── models.yaml         # Task profiles (incl. web_research)
├── routers/
│   ├── chat.py             # /chat, /chat/stream, /chat/regenerate
│   ├── sentiment.py        # POST /sentiment/analyze, history
│   ├── provider_settings.py
│   ├── generations.py
│   ├── documents.py
│   └── ...
├── services/
│   ├── chat_service.py
│   ├── web_research_service.py
│   ├── web_search.py
│   ├── web_scraper.py
│   ├── url_security.py
│   ├── content_cleaner.py
│   ├── sentiment_context.py
│   ├── rag_service.py
│   ├── router_engine.py
│   └── ...
└── tests/                  # 152 tests
```

---

## Chat Pipeline

```
User message
    │
    ├─► POST /sentiment/analyze (async, parallel — UI panel)
    │
    ▼
analyze_prompt()           ← llm_classifier or keyword fallback
    │
    ▼
detect_generation_intent() ← chat | document | image
    │
    ▼
build_context()            ← Prompt Intelligence v2 (if enabled)
    │
    ▼
retrieve_for_chat()        ← RAG top-3 chunks (ChromaDB)
    │
    ▼
retrieve_web_for_chat()    ← search + scrape OR direct URL
    │                         fallback if bot-protected
    ▼
resolve_sentiment_for_turn() ← tone guidance → system prompt
    │
    ▼
route()                    ← enabled models (provider ∧ admin ∧ user)
    │
    ▼
generate / stream          ← model_clients (LiteLLM)
    │
    ▼
persist + activity log + analytics
```

---

## Web Research Flow

```
Trigger: web_research task | keywords | URL in prompt
    │
    ├─ URLs in prompt? ──► scrape direct (skip search)
    │       │
    │       └─ fail + TAVILY/SERPER set? ──► search fallback
    │
    └─ no URL ──► Tavily/Serper search ──► scrape top URLs
            │
            └─ scrape fail ──► inject search snippets
    │
    ▼
Inject into system_prompt with citation instructions
```

---

## Model Availability

```
enabled = provider_enabled AND admin_enabled AND user_enabled
```

---

## Frontend Structure

```
frontend/src/
├── App.jsx
├── components/
│   ├── ChatPage.jsx        # sidebar | thread | sentiment + routing
│   ├── SentimentPanel.jsx
│   ├── ModelControls.jsx
│   └── attachments/        # Generated file/image renderers
└── api/
    ├── chat.js             # streamChat() SSE
    ├── sentiment.js
    └── settings.js
```

**Chat routing panel badges:** Document Context Used, 🌐 Web Research, Sentiment-aware response, generation modality.

---

## Streaming (SSE)

`POST /chat/stream` events: `routing_start`, `routing_complete`, `token`, `generation_*`, `artifact`, `complete`, `error`.

`routing_complete` and `complete` include `web_research_used`, `web_sources`, `web_fallback_used`, sentiment fields.

---

## Data Model (key tables)

| Table | Purpose |
|-------|---------|
| `model_runs` | Routing, RAG metadata, **web research metadata**, costs |
| `message_sentiments` | Per-user-message tone analysis |
| `provider_settings` | Org-wide provider enable/disable |
| `uploaded_documents` | RAG file metadata |
| `activity_logs` | `web_research_started/completed`, routing, RAG, etc. |

Web research on `model_runs`: `web_research_used`, `web_search_query`, `web_search_provider`, `web_sources_json`, `web_scrape_duration_ms`.

---

## Deployment

| Service | Host |
|---------|------|
| API | Render |
| Frontend | Vercel |
| SQLite + ChromaDB + generated files | Render disk (optional) |

See [deploy-render.md](deploy-render.md) and [deploy-vercel.md](deploy-vercel.md).
