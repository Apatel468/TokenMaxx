# SmartLLM Router — Project Memory

> **Permanent project context.** This file is the single source of truth when chat history is unavailable.  
> **Version:** 0.2.2 · **Last audited:** June 2026  
> **GitHub:** https://github.com/Apatel468/smartllm-router

---

## Project Vision

**SmartLLM Router** is a demo/MVP web application that intelligently routes user prompts to the most cost-effective AI model while maintaining acceptable quality. It proves the concept of **task-aware model selection**, **prompt engineering**, and **cost savings tracking** compared to always using an expensive premium model (GPT-4o baseline).

The product narrative: *"Don't pay premium prices for simple tasks — classify the request, engineer the prompt, route to the right Groq model, and show how much you saved."*

---

## Business Problem Being Solved

Organizations and developers often default to one expensive LLM (e.g. GPT-4o) for every request. Many tasks — flashcards, simple Q&A, summarization — do not need premium reasoning. SmartLLM Router:

1. **Classifies** what kind of task the user is asking for (keyword rules; LLM classifier optional upgrade)
2. **Enhances** the prompt with task-specific structure (AI agent or rule fallback)
3. **Routes** to a cheaper Groq model configured for that task type in `models.yaml`
4. **Tracks** estimated token cost vs. a premium baseline
5. **Persists** conversations, titles, and analytics for audit and demo purposes

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  React + Vite Frontend (localhost:5173 or 5174)              │
│  Tabs: Chat (3-column) | Analytics Dashboard                 │
└────────────────────────────┬─────────────────────────────────┘
                             │ REST JSON → http://127.0.0.1:8001
┌────────────────────────────▼─────────────────────────────────┐
│  FastAPI Backend (127.0.0.1:8001)                            │
│  Routers: /chat /conversations /analytics/* /models /health  │
└────────────────────────────┬─────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
 prompt_analyzer      prompt_enhancer         router_engine
 (keyword classify)   (Groq AI agent + rules) (models.yaml)
     │                       │                       │
     └──────────► context_builder ◄──────────────────┘
                             │
                    model_clients (LiteLLM → Groq)
                    response_cleaner (strip thinking tags)
                             │
              cost_tracker + conversation_store
              conversation_title (after first reply)
                             │
                             ▼
              SQLite: smartllm_router.db
              (conversations, messages, model_runs)
```

**Per chat request with `GROQ_API_KEY`:**
- **First turn of a new conversation:** up to **3 Groq calls** — prompt engineer, response model, conversation title
- **Follow-up turns:** up to **2 Groq calls** — prompt engineer, response model (title already stored)

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
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/models.yaml
│   ├── routers/ (chat, conversations, analytics, models)
│   └── services/
│       ├── prompt_analyzer.py    # Keyword classifier (+ default difficulty/risk)
│       ├── prompt_enhancer.py    # AI prompt engineering agent + rule fallback
│       ├── context_builder.py
│       ├── router_engine.py      # Groq routing from models.yaml
│       ├── config_loader.py
│       ├── model_clients.py
│       ├── response_cleaner.py
│       ├── cost_tracker.py       # YAML pricing + log_request_metrics
│       ├── conversation_store.py
│       ├── conversation_title.py
│       └── report_generator.py
├── frontend/src/
│   ├── components/ (ChatPage, AnalyticsDashboard)
│   ├── api/ (chat, conversations, analytics, config.js)
│   └── utils/conversationTitle.js
└── docs/
```

---

## Current Implementation Status

| Area | Status |
|------|--------|
| Backend core pipeline | ✅ Complete |
| Groq + LiteLLM integration | ✅ Complete |
| YAML-driven Groq routing (`router_engine.py`) | ✅ Complete |
| Keyword task classifier | ✅ Complete |
| LLM task classifier (Phase 3B) | ⚠️ Optional upgrade — not in code yet |
| AI prompt engineering agent | ✅ Complete (Phase 4) |
| Rule-based fallbacks (classify + enhance + title) | ✅ Complete |
| Mock fallback (no API key) | ✅ Complete |
| SQLite persistence + enhancement fields | ✅ Complete |
| Multi-turn conversations | ✅ Complete (Phase 3A) |
| Conversation titles (AI + fallback) | ✅ Complete |
| Response cleanup (Qwen thinking tags) | ✅ Complete |
| Analytics API + dashboard | ✅ Complete |
| Frontend chat UI (3-column, 100vh) | ✅ Complete |
| Frontend shows enhancement fields | ❌ Not started |
| Auth / multi-user | ❌ Not started |
| Streaming responses | ❌ Not started |
| Tests | ❌ Not started |
| Production deploy | ❌ Not started |

---

## Completed Features

### Phase 2 — Groq + YAML Routing
- `router_engine.py` reads `config/models.yaml` via `config_loader`
- Returns `RoutingDecision` with `model_id`, `groq_model`, `provider`, `model_label`, `reason`
- `cost_tracker.py` uses YAML `pricing` and `premium_baseline`; logs via `log_request_metrics()`

### Phase 3B — Classifier (current vs planned)
- **Current:** Keyword matching in `prompt_analyzer.py`
- **Returns:** `task_type`, `confidence`, `keywords_matched`, `difficulty` (default `"medium"`), `risk_level` (default `"low"`)
- **Planned:** Groq LLM classifier using `models.yaml` → `classifier` block

### Phase 4 — Prompt Engineering
- `prompt_enhancer.py` — Groq `llama-3.1-8b-instant` AI agent + rule fallback
- `POST /chat` returns `original_prompt`, `enhanced_prompt`, `enhancement_method`, etc.

### Phase 4+ — UX & Polish
- **Titles** — generated after first assistant reply from user + assistant text; 3–8 words; stored in `conversations.title`
- **Response cleanup** — `response_cleaner.py` strips Qwen `<think>` tags
- **UI** — 100vh, 3-column chat, analytics dashboard
- **CORS** — `main.py` allows frontend on ports 5173 and 5174

---

## POST /chat Pipeline (Current)

```
1. Load prior messages (optional conversation_id)
2. prompt_analyzer.analyze_prompt()     → task_type, confidence, difficulty, risk_level
3. context_builder.build_context()      → prompt_enhancer.enhance_prompt()
4. router_engine.route()                → Groq model from models.yaml
5. model_clients.generate_response()    → LiteLLM + system prompt + history
6. response_cleaner.clean_model_response()
7. cost_tracker.estimate_costs() + log_request_metrics()
8. conversation_store.save_chat_turn()  → SQLite + title if first reply
9. ChatResponse JSON
```

---

## API Endpoints (Quick Reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check |
| POST | `/chat` | Full pipeline; optional `conversation_id` |
| GET | `/conversations` | List summaries (backfills missing titles) |
| GET | `/conversations/{id}` | Full thread + title |
| GET | `/analytics/summary` | Aggregate cost/savings |
| GET | `/analytics/history` | Per `model_run` history |
| GET | `/analytics/model-usage` | Per-model stats |
| GET | `/models` | Groq catalog from YAML |
| GET | `/docs` | Swagger UI |

### POST /chat Response Fields (key)

| Field | Description |
|-------|-------------|
| `conversation_id` | Thread id |
| `title` | Set after first assistant reply |
| `original_prompt` | What the user typed |
| `enhanced_prompt` | Prompt sent to the response model |
| `enhancement_method` | `"ai"` or `"rule_fallback"` |
| `selected_model` | e.g. `Groq / llama-3.1-8b-instant` |
| `mock_response` | Response text (legacy field name) |

---

## Groq Models in Use

| Role | Model | Config location |
|------|-------|-----------------|
| Prompt engineer | `llama-3.1-8b-instant` | `prompt_enhancer.py` |
| Conversation title | `llama-3.1-8b-instant` | `conversation_title.py` |
| Classifier (planned) | `llama-3.1-8b-instant` | `models.yaml` → `classifier` |
| flashcards / report | `llama-3.3-70b-versatile` | `models.yaml` → `models` |
| coding | `qwen/qwen3-32b` | `models.yaml` → `models` |
| general_qa | `llama-3.1-8b-instant` | `models.yaml` → `models` |
| Savings baseline | GPT-4o rates | `models.yaml` → `premium_baseline` |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Optional* | Enhancer, title, and chat via LiteLLM |

\*Without it: keyword classify, rule enhance/title, mock responses.

**Security rule:** Never read, log, or commit `.env` contents.

---

## How to Run

### First-time setup

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
copy .env.example .env         # add GROQ_API_KEY

# Frontend
cd frontend
npm install
```

### Every run (two terminals)

```bash
# Terminal 1 — Backend
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8001

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### URLs

| What | URL |
|------|-----|
| App | http://localhost:5173 (or **5174** if 5173 is busy) |
| API docs | http://127.0.0.1:8001/docs |
| Health | http://127.0.0.1:8001/health |

Frontend API base is hardcoded in `frontend/src/api/config.js` → `http://127.0.0.1:8001`.

### Sharing the project

Send the GitHub repo or a zip. **Do not** include `backend/.env`, `venv/`, or `node_modules/`. Recipient creates their own `.env` with a Groq key from https://console.groq.com.

---

## Known Bugs & Technical Debt

- `main.py` module docstring still mentions port 8000
- LLM classifier not implemented — keyword + default difficulty/risk only
- No context length limits — long threads may hit Groq token limits
- `ChatResponse.mock_response` legacy field name
- Config YAML cached — restart server after `models.yaml` edits
- Frontend does not display enhancement fields yet
- No Alembic migrations (startup ALTER only)
- Legacy `chat_history` table unused
- No automated tests

---

## Recommended Next Steps

1. **Restore LLM classifier** in `prompt_analyzer.py` (optional quality upgrade)
2. **Frontend** — Show original vs enhanced prompt in Chat UI
3. **Context truncation** for long threads
4. **`VITE_API_BASE`** env variable for frontend
5. **Tests** — pytest for pipeline services
6. **Push local fixes** — `router_engine`, `cost_tracker`, `prompt_analyzer`, CORS (if not yet committed)

---

# CURSOR HANDOFF PROMPT

```
You are continuing development on SmartLLM Router.

READ FIRST: docs/project_memory.md, architecture.md, decisions.md, roadmap.md
GITHUB: https://github.com/Apatel468/smartllm-router

RUN:
  cd backend && venv\Scripts\python -m uvicorn main:app --reload --port 8001
  cd frontend && npm run dev

KEY FILES:
- backend/routers/chat.py
- backend/services/router_engine.py      # YAML Groq routing
- backend/services/prompt_analyzer.py      # keyword classify
- backend/services/prompt_enhancer.py
- backend/services/cost_tracker.py         # YAML pricing
- backend/services/conversation_title.py
- backend/config/models.yaml
- frontend/src/api/config.js               # API_BASE :8001

GROQ CALLS (with key): enhance → respond → title (first turn only)
CONSTRAINTS: Groq-only, port 8001, never read/log .env
```

---
