# SmartLLM Router — Project Memory

> **Permanent project context.** This file is the single source of truth when chat history is unavailable.  
> **Version:** 0.2.1 · **Last audited:** June 2026  
> **GitHub:** https://github.com/Apatel468/smartllm-router

---

## Project Vision

**SmartLLM Router** is a demo/MVP web application that intelligently routes user prompts to the most cost-effective AI model while maintaining acceptable quality. It proves the concept of **task-aware model selection**, **prompt engineering**, and **cost savings tracking** compared to always using an expensive premium model (GPT-4o baseline).

The product narrative: *"Don't pay premium prices for simple tasks — classify the request, engineer the prompt, route to the right Groq model, and show how much you saved."*

---

## Business Problem Being Solved

Organizations and developers often default to one expensive LLM (e.g. GPT-4o) for every request. Many tasks — flashcards, simple Q&A, summarization — do not need premium reasoning. SmartLLM Router:

1. **Classifies** what kind of task the user is asking for (keyword rules today; LLM classifier planned/restored in Phase 3B)
2. **Enhances** the prompt with task-specific structure (AI agent or rule fallback)
3. **Routes** to a cheaper Groq model configured for that task type
4. **Tracks** estimated token cost vs. a premium baseline
5. **Persists** conversations, titles, and analytics for audit and demo purposes

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  React + Vite Frontend (localhost:5173)                      │
│  Tabs: Chat (3-column) | Analytics Dashboard                 │
└────────────────────────────┬─────────────────────────────────┘
                             │ REST JSON
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

Models used: `llama-3.1-8b-instant` (enhancer, title), routed model from YAML (70B, Qwen, or 8B instant).

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
│       ├── prompt_analyzer.py    # Keyword classifier (LLM path planned)
│       ├── prompt_enhancer.py    # AI prompt engineering agent + rule fallback
│       ├── context_builder.py
│       ├── router_engine.py
│       ├── config_loader.py
│       ├── model_clients.py
│       ├── response_cleaner.py   # Strip <think> from Qwen output
│       ├── cost_tracker.py
│       ├── conversation_store.py
│       ├── conversation_title.py # ChatGPT-style titles after first reply
│       └── report_generator.py
├── frontend/src/
│   ├── components/ (ChatPage, AnalyticsDashboard)
│   ├── api/ (chat, conversations, analytics)
│   └── utils/conversationTitle.js
└── docs/
    ├── project_memory.md
    ├── architecture.md
    ├── roadmap.md
    └── decisions.md
```

---

## Current Implementation Status

| Area | Status |
|------|--------|
| Backend core pipeline | ✅ Complete |
| Groq + LiteLLM integration | ✅ Complete |
| Keyword task classifier | ✅ Complete |
| LLM task classifier (Phase 3B) | ⚠️ Documented but not in current `prompt_analyzer.py` |
| AI prompt engineering agent | ✅ Complete (Phase 4) |
| Rule-based fallbacks (classify + enhance) | ✅ Complete |
| Mock fallback (no API key) | ✅ Complete |
| YAML-driven routing | ✅ Complete |
| SQLite persistence + enhancement fields | ✅ Complete |
| Multi-turn conversations | ✅ Complete (Phase 3A) |
| Conversation titles (AI + fallback) | ✅ Complete |
| Response cleanup (Qwen thinking tags) | ✅ Complete |
| Analytics API + dashboard | ✅ Complete |
| Analytics history per model_run | ✅ Complete |
| Frontend chat UI (3-column, 100vh) | ✅ Complete |
| Frontend shows enhancement fields | ❌ Not started |
| Auth / multi-user | ❌ Not started |
| Streaming responses | ❌ Not started |
| Tests | ❌ Not started |
| Production deploy | ❌ Not started |

**Development maturity:** Functional local MVP with AI prompt engineering and cost routing. Not production-ready.

---

## Completed Features

### Phase 1 — MVP Backend
- FastAPI, keyword classifier, mock responses, cost tracking

### Phase 2 — Groq + LiteLLM
- Real Groq completions, YAML routing, mock fallback

### Phase 3 — Analytics
- `conversations`, `messages`, `model_runs` tables
- Analytics endpoints + dashboard

### Phase 3A — Conversation Memory
- Multi-turn `conversation_id`, full history to Groq, sidebar UI

### Phase 3B — LLM Classifier (planned / partially reverted)
- **Design:** Groq `llama-3.1-8b-instant` via LiteLLM; JSON with `task_type`, `difficulty`, `risk_level`
- **Current code:** `prompt_analyzer.py` is keyword-only (`task_type`, `confidence`, `keywords_matched`)
- **Action needed:** Restore LLM classifier or add `difficulty`/`risk_level` defaults so `context_builder` works

### Phase 4 — Prompt Engineering
- `prompt_enhancer.py` — AI Prompt Engineering Agent (Groq `llama-3.1-8b-instant`)
- Returns JSON: `enhanced_prompt`, `system_prompt`, `enhancement_reason`
- Rule-based fallback when Groq fails or no API key
- `enhancement_method` in API: `"ai"` or `"rule_fallback"`
- `model_runs` stores `enhanced_prompt`, `system_prompt`, `enhancement_reason`
- `POST /chat` returns original + enhanced prompts and enhancement metadata
- `model_clients` prepends `system_prompt` to LiteLLM messages

### Phase 4+ — UX & Polish
- **`conversation_title.py`** — titles generated **after the first assistant reply** using both the first user message and first assistant response; 3–8 words, ChatGPT-style; stored once in `conversations.title`
- **`response_cleaner.py`** — strips `<think>` blocks from model output (Qwen)
- **`POST /chat`** returns `title` when generated on that turn
- **Frontend:** 100vh layout, internal scroll, 3-column chat (sidebar | thread | routing), analytics dashboard with KPIs + model usage + recent conversations
- **Sidebar:** shows stored title or `"New Chat"` until first reply completes

### Frontend
- Chat + Analytics tabs; API base `http://127.0.0.1:8001`

---

## POST /chat Pipeline (Current)

```
1. Load prior messages (optional conversation_id)
2. prompt_analyzer.analyze_prompt()     → task_type, confidence, keywords_matched
3. context_builder.build_context()      → calls prompt_enhancer.enhance_prompt()
4. router_engine.route()                → Groq model from models.yaml
5. model_clients.generate_response()    → system + enhanced history → Groq
6. response_cleaner.clean_model_response() → strip thinking tags
7. cost_tracker.estimate_costs()
8. conversation_store.save_chat_turn()  → SQLite + generate title if missing
9. ChatResponse JSON (includes title when set)
```

---

## API Endpoints (Quick Reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check |
| POST | `/chat` | Full pipeline; optional `conversation_id` |
| GET | `/conversations` | List conversation summaries (backfills missing titles) |
| GET | `/conversations/{id}` | Full message thread + title |
| GET | `/analytics/summary` | Aggregate cost/savings |
| GET | `/analytics/history` | Recent turns (per `model_run`, includes `enhanced_prompt`) |
| GET | `/analytics/model-usage` | Per-model stats |
| GET | `/models` | Groq catalog from YAML |
| GET | `/docs` | Swagger UI |

### POST /chat Response Fields (key)

| Field | Description |
|-------|-------------|
| `conversation_id` | Thread id (new or existing) |
| `title` | Conversation title (set after first assistant reply; empty on follow-ups if already stored) |
| `original_prompt` | What the user typed |
| `enhanced_prompt` | AI/rule-wrapped prompt sent to response model |
| `system_prompt` | System instructions for response model |
| `enhancement_reason` | Why enhancement was applied |
| `enhancement_method` | `"ai"` or `"rule_fallback"` |
| `task_type` | Classified task |
| `selected_model` | Routed Groq model label |
| `mock_response` | AI response text (legacy field name) |

---

## Groq Models in Use

| Role | Model | Config location |
|------|-------|-----------------|
| Classifier (planned) | `llama-3.1-8b-instant` | `models.yaml` → `classifier` |
| Prompt engineer | `llama-3.1-8b-instant` | Hardcoded in `prompt_enhancer.py` |
| Conversation title | `llama-3.1-8b-instant` | Hardcoded in `conversation_title.py` |
| flashcards / report | `llama-3.3-70b-versatile` | `models.yaml` → `models` |
| coding | `qwen/qwen3-32b` | `models.yaml` → `models` |
| general_qa | `llama-3.1-8b-instant` | `models.yaml` → `models` |
| Savings baseline (not called) | GPT-4o rates | `models.yaml` → `premium_baseline` |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Optional* | Prompt engineer, title generator, and chat via LiteLLM |

\*Without it: keyword classify, rule-based enhance, rule-based titles, mock chat responses.

**Security rule:** Never read, log, or commit `.env` contents.

---

## How to Run

```bash
cd backend
venv\Scripts\python -m uvicorn main:app --reload --port 8001

cd frontend
npm run dev
# → http://localhost:5173
```

---

## Known Bugs & Technical Debt

- **`prompt_analyzer.py` regression:** Keyword-only; missing `difficulty`/`risk_level` that `context_builder` expects — chat may fail until fixed or LLM classifier restored
- `main.py` docstring still mentions port 8000
- No context length limits — long threads may hit Groq token limits
- `ChatResponse.mock_response` legacy field name
- Config YAML cached — restart server after edits
- Frontend does not display enhancement fields yet
- No Alembic migrations (uses `create_all` + manual ALTER for new columns)
- Legacy `chat_history` table orphaned
- No automated tests
- Old conversations may have stale titles unless `title` column cleared to regenerate

---

## Recommended Next Steps

1. **Fix classifier** — Restore LLM classifier in `prompt_analyzer.py` or add default `difficulty`/`risk_level` to `AnalysisResult`
2. **Frontend** — Show `enhancement_method`, original vs enhanced prompt in Chat UI
3. **Context truncation** — Sliding window before Groq calls
4. **`VITE_API_BASE`** — Env-based frontend API URL
5. **Streaming** — SSE for response generation
6. **Tests** — Unit tests for analyzer, enhancer, title, cost_tracker; one integration test
7. **Alembic** — Proper migrations before production

---

# CURSOR HANDOFF PROMPT

Copy everything below into a **new Cursor chat** to continue development:

---

```
You are continuing development on SmartLLM Router — an MVP that classifies prompts,
engineers them with an AI agent, routes to cost-effective Groq models via LiteLLM,
tracks savings vs GPT-4o baseline, and stores conversations in SQLite.

READ FIRST:
1. docs/project_memory.md
2. docs/architecture.md
3. docs/decisions.md
4. docs/roadmap.md

GITHUB: https://github.com/Apatel468/smartllm-router

STACK:
- Backend: FastAPI + SQLAlchemy + SQLite + LiteLLM (Groq only)
- Frontend: React 18 + Vite
- Config: backend/config/models.yaml
- Secrets: GROQ_API_KEY in backend/.env — NEVER read or log .env contents

RUN:
  cd backend && venv\Scripts\python -m uvicorn main:app --reload --port 8001
  cd frontend && npm run dev

KEY FILES:
- backend/routers/chat.py — POST /chat orchestration
- backend/services/prompt_analyzer.py — keyword classifier (LLM restore needed)
- backend/services/prompt_enhancer.py — Groq AI prompt agent + rule fallback
- backend/services/context_builder.py — enhancement + message_history
- backend/services/conversation_title.py — titles after first reply (user + assistant)
- backend/services/conversation_store.py — save turns, persist titles once
- backend/services/response_cleaner.py — strip Qwen thinking tags
- backend/services/router_engine.py — YAML routing
- backend/services/model_clients.py — LiteLLM chat + system prompt prepend
- backend/config/models.yaml — classifier, routes, pricing
- frontend/src/components/ChatPage.jsx — 3-column chat UI
- frontend/src/utils/conversationTitle.js — title placeholder until API returns

POST /chat FLOW:
1. Load prior messages (optional conversation_id)
2. analyze_prompt() → task_type (+ difficulty/risk when classifier fixed)
3. build_context() → enhance_prompt() → enhanced_prompt, system_prompt
4. route() → Groq model from YAML
5. generate_response() → litellm with system + enhanced history
6. clean_model_response() → strip thinking tags
7. estimate_costs() + save_chat_turn() → generate title if first reply

GROQ CALLS (with API key): prompt engineer (8B) → response model (routed) → title (8B, first turn only)

CURRENT PHASE: 4+ (titles, UI polish). Next: fix classifier, enhancement UI, truncation, tests.

CONSTRAINTS: Beginner-friendly comments, Groq-only, port 8001, do not commit .env
```

---
