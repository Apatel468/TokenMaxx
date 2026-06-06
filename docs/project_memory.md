# SmartLLM Router — Project Memory

> **Permanent project context.** This file is the single source of truth when chat history is unavailable.  
> **Version:** 0.1.0 MVP · **Last audited:** June 2026

---

## Project Vision

**SmartLLM Router** is a demo/MVP web application that intelligently routes user prompts to the most cost-effective AI model while maintaining acceptable quality. It proves the concept of **task-aware model selection** and **cost savings tracking** compared to always using an expensive premium model (GPT-4o baseline).

The product narrative: *"Don't pay premium prices for simple tasks — let the router pick the right Groq model for the job and show you how much you saved."*

---

## Business Problem Being Solved

Organizations and developers often default to one expensive LLM (e.g. GPT-4o) for every request. Many tasks — flashcards, simple Q&A, summarization — do not need premium reasoning. SmartLLM Router:

1. **Classifies** what kind of task the user is asking for
2. **Routes** to a cheaper Groq model configured for that task type
3. **Tracks** estimated token cost vs. a premium baseline
4. **Persists** conversations and analytics for audit and demo purposes

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  React + Vite Frontend (localhost:5173)                      │
│  Tabs: Chat (multi-turn + sidebar) | Analytics Dashboard     │
└────────────────────────────┬─────────────────────────────────┘
                             │ REST JSON
┌────────────────────────────▼─────────────────────────────────┐
│  FastAPI Backend (127.0.0.1:8001)                            │
│  Routers: /chat /conversations /analytics/* /models /health  │
└────────────────────────────┬─────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
 prompt_analyzer      router_engine            model_clients
 (keyword classify)   (config/models.yaml)     (LiteLLM → Groq)
     │                       │                       │
     └──────────► context_builder ◄─────────────────┘
                             │
              cost_tracker + conversation_store
                             │
                             ▼
              SQLite: smartllm_router.db
              (conversations, messages, model_runs)
```

---

## Technologies Used

| Layer | Technology |
|-------|------------|
| Backend API | Python 3, FastAPI 0.109+ |
| Server | Uvicorn |
| ORM / DB | SQLAlchemy 2.x, SQLite |
| LLM gateway | LiteLLM 1.40+ |
| LLM provider | Groq (only active provider) |
| Config | YAML (`config/models.yaml`), python-dotenv |
| Frontend | React 18, Vite 6 |
| Styling | Plain CSS (no Tailwind/UI library) |

---

## Folder Structure

```
smartllm-router/
├── backend/
│   ├── main.py                    # App entry, CORS, logging, router mounts
│   ├── database.py                # SQLAlchemy models + engine
│   ├── models.py                  # Pydantic API schemas
│   ├── requirements.txt
│   ├── .env.example               # GROQ_API_KEY template (never commit .env)
│   ├── .gitignore
│   ├── smartllm_router.db         # Runtime SQLite (gitignored)
│   ├── config/
│   │   └── models.yaml            # Routing, pricing, premium baseline
│   ├── routers/
│   │   ├── chat.py
│   │   ├── conversations.py
│   │   ├── analytics.py
│   │   └── models.py
│   └── services/
│       ├── prompt_analyzer.py
│       ├── context_builder.py
│       ├── router_engine.py
│       ├── config_loader.py
│       ├── model_clients.py
│       ├── cost_tracker.py
│       ├── conversation_store.py
│       └── report_generator.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── App.css / index.css
│       ├── api/ (config.js, chat.js, conversations.js, analytics.js)
│       └── components/ (ChatPage.jsx, AnalyticsDashboard.jsx)
└── docs/                          # THIS FOLDER — permanent memory
    ├── project_memory.md
    ├── architecture.md
    ├── roadmap.md
    └── decisions.md
```

**Originally planned but NOT created:** `docs/system_design.md`, `docs/model_catalog.md`, `docs/demo_script.md`

---

## Current Implementation Status

| Area | Status |
|------|--------|
| Backend core pipeline | ✅ Complete |
| Groq + LiteLLM integration | ✅ Complete |
| Mock fallback (no API key) | ✅ Complete |
| YAML-driven routing | ✅ Complete |
| SQLite persistence | ✅ Complete |
| Multi-turn conversations | ✅ Complete (Phase 3A) |
| Analytics API + dashboard | ✅ Complete |
| Frontend chat UI | ✅ Complete |
| Auth / multi-user | ❌ Not started |
| Streaming responses | ❌ Not started |
| Tests | ❌ Not started |
| Production deploy | ❌ Not started |
| Multi-provider routing | ❌ Removed (Groq-only pivot) |

**Development maturity:** Functional local MVP suitable for demos and iteration. Not production-ready.

---

## Completed Features

### Phase 1 — MVP Backend
- FastAPI app with `/health` and `POST /chat`
- Keyword-based task classification (`prompt_analyzer.py`)
- Mock model responses without API keys
- Cost estimation vs GPT-4o premium baseline
- Beginner-friendly comments throughout

### Phase 2 — Real AI (Groq-only pivot)
- LiteLLM integration
- `GROQ_API_KEY` from `.env` (presence check only in code — never log/read key value in tooling)
- Real Groq completions via `litellm.completion()`
- Automatic mock fallback on missing key or API errors
- Routing moved to `config/models.yaml`

### Phase 3 — Analytics
- SQLite tables: `conversations`, `messages`, `model_runs`
- `GET /analytics/summary`, `/analytics/history`, `/analytics/model-usage`
- Frontend Analytics Dashboard tab

### Phase 3A — Conversation Memory
- Optional `conversation_id` on `POST /chat`
- Load prior messages → build full context → send to Groq
- `GET /conversations`, `GET /conversations/{id}`
- Frontend: conversation sidebar, message thread, New Chat button

### Frontend
- Chat tab with routing/cost panel
- Analytics tab with summary cards, model usage table, history list
- API base URL: `http://127.0.0.1:8001` (hardcoded in `frontend/src/api/config.js`)

---

## Unfinished / Incomplete Features

1. **Documentation originally scoped** — `system_design.md`, `model_catalog.md`, `demo_script.md` never written (replaced by this docs set)
2. **Streaming** — All responses are blocking; no SSE/WebSocket
3. **Token window management** — Full history sent every turn; no truncation
4. **Per-turn routing in threads** — Each new message re-classifies and may pick a different model (by design for now, may confuse users)
5. **Analytics for multi-turn** — `/analytics/history` shows only first user/assistant pair per conversation (see Known Bugs)
6. **Environment-based frontend API URL** — Port 8001 hardcoded
7. **Database migrations** — No Alembic; schema changes use `create_all` only
8. **Legacy `chat_history` table** — Orphaned; not written by current code
9. **Unit/integration tests** — None
10. **Additional LLM providers** — OpenAI/Anthropic/Gemini were explored then removed in Groq-only pivot

---

## API Endpoints (Quick Reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check |
| POST | `/chat` | Send prompt; optional `conversation_id` |
| GET | `/conversations` | List conversation summaries |
| GET | `/conversations/{id}` | Full message thread |
| GET | `/analytics/summary` | Aggregate cost/savings |
| GET | `/analytics/history` | Recent chat rows |
| GET | `/analytics/model-usage` | Per-model stats |
| GET | `/models` | Groq model catalog from YAML |
| GET | `/docs` | Swagger UI |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Optional* | Groq API access via LiteLLM |

\*Without it, all responses are mocks. Copy `backend/.env.example` → `backend/.env`.

**Security rule for contributors/agents:** Never read, log, or commit `.env` contents.

---

## How to Run

```bash
# Backend (use port 8001 — port 8000 often conflicts on Windows)
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt   # Windows
cp .env.example .env                           # add GROQ_API_KEY
venv\Scripts\python -m uvicorn main:app --reload --port 8001

# Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Known Bugs & Technical Debt

See `docs/decisions.md` and `docs/architecture.md` for detail. Summary:

- Port 8000 conflict on some machines; use **8001**
- `main.py` docstring still mentions port 8000
- Analytics history incomplete for multi-turn conversations (only first exchange)
- Keyword classifier misroutes ambiguous prompts
- No context length limits — long threads may hit Groq token limits
- `ChatResponse.mock_response` field name is legacy (holds real responses too)
- Config YAML cached in memory — file edits require server restart
- `report_generator.get_conversations` used by analytics duplicates logic in `conversation_store`

---

## Important Project Context

- Built as a **beginner-friendly learning MVP** with extensive inline comments
- Evolved through phases: mock → multi-provider LiteLLM → **Groq-only** → analytics → multi-turn memory
- User explicitly requested **never accessing `.env` file contents** in AI tooling
- Database was reset at least once during development (`smartllm_router.db` deleted and recreated)
- `backend/venv/` exists locally; dependencies also installed to user Python in some sessions

---

## Recommended Next Steps

1. **Fix analytics multi-turn display** — History should show all turns or per-`model_run` rows
2. **Add context truncation** — Sliding window or summarize-old-messages before Groq call
3. **Frontend env config** — `VITE_API_BASE` instead of hardcoded 8001
4. **Streaming responses** — Better UX for long Groq outputs
5. **Tests** — At minimum: prompt_analyzer, config_loader, cost_tracker unit tests; one `/chat` integration test
6. **Alembic migrations** — Before schema changes in production
7. **Remove or migrate `chat_history`** legacy table

---

# CURSOR HANDOFF PROMPT

Copy everything below into a **new Cursor chat** to continue development:

---

```
You are continuing development on SmartLLM Router — an MVP that routes user prompts to cost-effective Groq models via LiteLLM, tracks savings vs GPT-4o premium baseline, and stores conversations in SQLite.

READ FIRST (in order):
1. docs/project_memory.md  — full project context
2. docs/architecture.md    — system design and data flows
3. docs/decisions.md       — do-not-break rules
4. docs/roadmap.md         — what's done and what's next

STACK:
- Backend: Python FastAPI + SQLAlchemy + SQLite + LiteLLM (Groq only)
- Frontend: React 18 + Vite, plain CSS
- Config: backend/config/models.yaml (routing + pricing)
- Secrets: GROQ_API_KEY in backend/.env — NEVER read or log .env contents

RUN:
  cd backend && venv\Scripts\python -m uvicorn main:app --reload --port 8001
  cd frontend && npm run dev
  Frontend: http://localhost:5173
  API docs: http://127.0.0.1:8001/docs

KEY FILES:
- backend/routers/chat.py — main POST /chat pipeline
- backend/services/prompt_analyzer.py — keyword task classification
- backend/services/router_engine.py — reads models.yaml
- backend/services/model_clients.py — LiteLLM Groq + mock fallback
- backend/services/conversation_store.py — multi-turn SQLite persistence
- backend/config/models.yaml — edit routing without code changes
- frontend/src/components/ChatPage.jsx — multi-turn UI with sidebar
- frontend/src/api/config.js — API_BASE = http://127.0.0.1:8001

POST /chat FLOW:
1. Optional conversation_id → load prior messages from SQLite
2. analyze_prompt(latest message) → task_type
3. build_context → token estimate + message_history
4. route(task_type) → Groq model from YAML
5. generate_response → litellm.completion with full history
6. estimate_costs → vs GPT-4o baseline from YAML
7. save_chat_turn → conversations + messages + model_runs

TASK TYPES (analyzer): coding, summarization, creative_writing, data_analysis, flashcards, report, general_qa, translation
YAML ROUTES: flashcards, coding, general_qa, report (+ aliases for other analyzer types)

CURRENT PHASE: 3A complete. Next priorities in docs/roadmap.md — likely analytics multi-turn fix, context truncation, tests.

CONSTRAINTS:
- Keep code beginner-friendly and commented
- Do not commit .env
- Groq-only unless explicitly asked to add providers
- Match existing patterns in services/ and routers/
- Default backend port: 8001

Before making changes, read the relevant service files. Ask clarifying questions only if requirements are ambiguous.
```

---
