# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Permanent project context.** This file is the single source of truth when chat history is unavailable.  
> **Version:** 0.4.0 · **Last audited:** June 2026  
> **GitHub:** https://github.com/Apatel468/TokenMaxx (redirects from `smartllm-router`)

---

## Project Vision

**TokenMaxx** — *Maximum Intelligence, Minimum Cost* — is an enterprise-style demo/MVP that intelligently routes user prompts to the most cost-effective AI model while maintaining acceptable quality. It proves **LLM-powered task classification**, **Prompt Intelligence Engine v2**, **task-aware model selection**, **SSE streaming responses**, **org-wide and per-user model toggles**, **on-demand model regeneration**, **JWT authentication**, **admin usage visibility**, **analytics export**, and **cost savings tracking** compared to always using an expensive premium model (GPT-4o baseline).

The product narrative: *"Maximum Intelligence, Minimum Cost — classify the request, analyze and enhance the prompt by task and complexity, score allowed Groq models with task-specific bonuses, stream the response live, route to the best enabled option, let users retry with another model on demand, and show how much you saved."*

---

## Business Problem Being Solved

Organizations and developers often default to one expensive LLM (e.g. GPT-4o) for every request. Many tasks do not need premium reasoning. TokenMaxx:

1. **Authenticates** users with JWT so chats and analytics are per-account
2. **Classifies** what kind of task the user is asking for (LLM classifier with keyword fallback)
3. **Analyzes and enhances** prompts via Prompt Intelligence v2 (task type, complexity, persona, strategy)
4. **Scores** allowlisted Groq chat models using registry metadata, complexity-aware weights, and task-specific bonuses
5. **Routes** to the highest-scoring **available** model (`admin_enabled AND user_enabled`)
6. **Streams** assistant responses token-by-token over SSE (`POST /chat/stream`)
7. **Lets users regenerate** with any other allowed model — one LLM call per click
8. **Tracks** estimated token cost vs. a premium baseline
9. **Persists** conversations, titles, and analytics per user
10. **Reports** employee usage to admins and exports analytics as CSV for demos

---

## Groq Model Allowlist (v0.4.0)

Only models in `GROQ_MODEL_ALLOWLIST` (`config/model_registry.py`) are synced, routed, and shown in Model Controls.

| Model | Chat routing | Model Controls |
|-------|--------------|----------------|
| `llama-3.1-8b-instant` | ✅ | ✅ |
| `llama-3.3-70b-versatile` | ✅ | ✅ |
| `meta-llama/llama-4-scout-17b-16e-instruct` | ✅ | ✅ |
| `qwen/qwen3-32b` | ✅ | ✅ |
| `openai/gpt-oss-20b` | ✅ | ✅ |
| `openai/gpt-oss-120b` | ✅ | ✅ |
| `whisper-large-v3` | ❌ audio only | ❌ |

**To change allowlist:** edit `GROQ_MODEL_ALLOWLIST` and `MODEL_REGISTRY` in `model_registry.py`. Stale SQLite settings rows are cleaned on startup via `cleanup_stale_model_settings()`.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  React + Vite Frontend (localhost:5173 or 5174)                  │
│  Auth gate → Login / Signup                                        │
│  Tabs: Chat | Analytics | Model Controls | Admin (admins only)     │
│  Chat uses POST /chat/stream (SSE) + fetch ReadableStream          │
└────────────────────────────┬─────────────────────────────────────┘
                             │ REST JSON + SSE + Authorization: Bearer
                             │ → http://127.0.0.1:8001
┌────────────────────────────▼─────────────────────────────────────┐
│  FastAPI Backend (127.0.0.1:8001)                                │
│  Public: /auth/* /health                                         │
│  Protected: /chat /chat/stream /chat/regenerate /conversations   │
│             /analytics/* /models /model-settings /admin/*          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
 auth_service           prompt_analyzer         router_engine
 user_preferences       llm_classifier          model_scorer
 regenerate_service     prompt_intelligence v2  context_builder
     │                       │                       │
     └──────────► model_clients (LiteLLM → Groq, stream + sync) ◄──┘
                             │
              cost_tracker + conversation_store + chat_service
                             │
                             ▼
              SQLite: smartllm_router.db
```

**Per chat request with `GROQ_API_KEY` and enhancement ON:**
- **First turn:** up to **4 Groq calls** — classifier, enhancer, response model, title
- **Follow-up turns:** up to **3 Groq calls** — classifier, enhancer, response model
- **Enhancement OFF:** skips enhancer call (saves cost/latency)
- **Regenerate click:** **1 Groq call only** — reuses stored prompts; no re-classify/route
- **Frontend default:** `POST /chat/stream` (SSE); `POST /chat` still available for sync

---

## Technologies Used

| Layer | Technology |
|-------|------------|
| Backend API | Python 3, FastAPI 0.109+ |
| Server | Uvicorn |
| Streaming | Server-Sent Events (`StreamingResponse`) |
| ORM / DB | SQLAlchemy 2.x, SQLite |
| Auth | bcrypt, PyJWT (HS256 Bearer tokens) |
| LLM gateway | LiteLLM 1.40+ |
| LLM provider | Groq (allowlisted models only) |
| Config | YAML (`config/models.yaml`), Python registry (`config/model_registry.py`) |
| Frontend | React 18, Vite 6 |
| Styling | Plain CSS |
| Tests | pytest, httpx (TestClient) — **39 tests** |

---

## Folder Structure

```
TokenMaxx/
├── backend/
│   ├── config/
│   │   ├── models.yaml
│   │   └── model_registry.py
│   ├── routers/
│   │   ├── auth.py, admin.py, chat.py      # /chat, /chat/stream, /chat/regenerate
│   │   └── conversations.py, analytics.py, ...
│   ├── services/
│   │   ├── prompt_intelligence.py   # Prompt Intelligence Engine v2
│   │   ├── prompt_enhancer.py       # thin wrapper → prompt_intelligence
│   │   ├── llm_classifier.py
│   │   ├── chat_service.py          # shared sync + stream pipeline
│   │   ├── model_scorer.py, router_engine.py
│   │   └── model_clients.py         # generate_response + stream_response
│   └── tests/                       # 39 pytest tests
├── frontend/src/
│   ├── components/ ChatPage, PromptEnhancementViewer, AnalyticsDashboard, ...
│   ├── api/ chat.js                 # streamChat() + regenerateChat()
│   └── utils/ exportAnalyticsReport.js
└── docs/
```

---

## Current Implementation Status

| Area | Status |
|------|--------|
| Backend core pipeline | ✅ Complete |
| Groq allowlist (6 chat models) | ✅ Complete |
| LLM task classifier + keyword fallback | ✅ Complete |
| Prompt Intelligence Engine v2 | ✅ Complete (v0.4.0) |
| Task-aware complexity routing | ✅ Complete |
| SSE streaming chat (`POST /chat/stream`) | ✅ Complete (v0.4.0) |
| Model Controls — org + personal toggles | ✅ Complete |
| JWT auth + admin dashboard | ✅ Complete |
| User prompt enhancement toggle | ✅ Complete |
| Prompt optimization viewer (v2 metadata) | ✅ Complete (v0.4.0) |
| Model regenerate (on-demand) | ✅ Complete |
| Top-5 recommendations + top-3 candidate scores | ✅ Complete |
| Analytics + CSV export | ✅ Complete |
| pytest suite | ✅ Complete (39 tests) |

---

## Prompt Intelligence Engine v2 (v0.4.0)

**Service:** `backend/services/prompt_intelligence.py` (via `prompt_enhancer.enhance_prompt`)

Analyze first, then enhance based on task type, complexity (0–100), and persona.

### PromptAnalysis fields

| Field | Description |
|-------|-------------|
| `original_prompt` | Exactly what the user typed |
| `task_type` | Normalized enhancement task (see below) |
| `complexity_score` | 0–100 |
| `complexity_level` | `simple`, `medium`, or `complex` |
| `persona` | Expert role for the downstream model |
| `output_format` | Expected response structure |
| `enhancement_strategy` | e.g. `minimal_clarity`, `structured_clarity`, `full_specification_*` |
| `enhanced_prompt` | Clean prompt sent to the model (no internal bracket notes) |

### Supported enhancement task types

`general_qa`, `coding`, `reasoning`, `writing`, `summarization`, `research`, `business`, `education`, `creative`, `data_analysis`

(Router task types like `report` → `business`, `math` → `reasoning` are normalized automatically.)

### Personas

| Task | Persona |
|------|---------|
| coding | Senior Software Engineer |
| business | Business Consultant |
| research | Research Analyst |
| writing | Professional Editor |
| education | Teacher/Tutor |
| data_analysis | Data Analyst |
| general_qa | Helpful Expert |

### Enhancement by complexity

| Level | Strategy | Behavior |
|-------|----------|----------|
| Simple (≤33) | `minimal_clarity` | Light touch; short Q&A often unchanged |
| Medium (34–66) | `structured_clarity` | Adds structure + output format |
| Complex (67+) | `full_specification_*` | Assumptions, constraints, steps, output format |

Returned in `ChatResponse.prompt_analysis` and stored on `model_runs`. UI: collapsible **View Prompt Optimization** panel.

---

## Task Classification (routing)

| Step | Service | Model | Fallback |
|------|---------|-------|----------|
| 1 | `llm_classifier.py` | `llama-3.1-8b-instant` | Keyword rules in `prompt_analyzer.py` |

**Routing task types:** `general_qa`, `classification`, `coding`, `math`, `reasoning`, `writing`, `summarization`, `report`, `creative`, `research`

---

## Task-Aware Routing

1. **Complexity score** (0–1) — prompt length, task type, keywords
2. **Dynamic weights** — cost/speed ↓ as complexity ↑
3. **Task-specific model bonuses** — steers picks per task type

| Task | Preferred models |
|------|------------------|
| Simple Q&A | `llama-3.1-8b-instant` |
| Coding / math | `qwen/qwen3-32b` |
| Writing / reports | `llama-3.3-70b-versatile`, `llama-4-scout` |
| Deep reasoning | `openai/gpt-oss-120b` |
| Balanced fallback | `openai/gpt-oss-20b` |

---

## SSE Streaming (v0.4.0)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat/stream` | Stream chat via Server-Sent Events |
| POST | `/chat` | Non-streaming (unchanged; used in tests) |

**SSE events:** `routing_start` → `routing_complete` → `token` (×N) → `complete` / `error`

- Real Groq streaming via LiteLLM `stream=True`; word-by-word fallback when unavailable
- DB save only after stream completes
- `routing_complete` includes routing metadata for Latest Routing panel
- Frontend: `streamChat()` in `api/chat.js`; live typing cursor in `ChatPage.jsx`

---

## POST /chat Pipeline (sync)

```
1. JWT → user_id
2. Load prior messages (optional conversation_id)
3. analyze_prompt() — LLM classify (keyword fallback)
4. build_context() — Prompt Intelligence v2 (if enhancement ON)
5. route() — complexity-aware score of available models
6. generate_response()
7. save_chat_turn() + ChatResponse (incl. prompt_analysis)
```

---

## API Endpoints (Quick Reference)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/chat` | Bearer | Full pipeline (non-streaming) |
| POST | `/chat/stream` | Bearer | SSE streaming pipeline |
| POST | `/chat/regenerate` | Bearer | User-selected model retry |
| GET | `/conversations/{id}` | Bearer | Thread + `prompt_analysis` on messages |
| GET | `/analytics/summary` | Bearer | Cost/savings KPIs |
| GET | `/analytics/history` | Bearer | Recent runs |
| GET | `/analytics/model-usage` | Bearer | Per-model stats |
| GET | `/model-settings` | Bearer | Model Controls |
| PUT | `/model-settings` | Bearer | Save model toggles |
| GET | `/admin/employee-usage` | Admin | Org-wide usage |

### ChatResponse key fields

| Field | Purpose |
|-------|---------|
| `prompt_analysis` | Prompt Intelligence v2 metadata |
| `classification_confidence` / `classification_reason` | Task classifier |
| `top_candidate_scores` | Top 3 routing scores |
| `top_recommendations` | Top 5 regenerate chips |
| `mock_response` | Assistant text (legacy field name) |

---

## How to Run

```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001
cd frontend && npm run dev
cd backend && source venv/bin/activate && pytest -v
```

| What | URL |
|------|-----|
| App | http://localhost:5173 |
| API docs | http://127.0.0.1:8001/docs |

---

## Known Bugs & Technical Debt

- Registry scores are editorial estimates
- `ChatResponse.mock_response` legacy field name
- No Alembic migrations
- JWT stateless — no server-side revoke
- Analytics PDF export not yet implemented (CSV only)
- Regenerate remains non-streaming

---

# CURSOR HANDOFF PROMPT

```
You are continuing development on TokenMaxx — Maximum Intelligence, Minimum Cost.

READ FIRST: docs/project_memory.md, architecture.md, system_design.md

RUN:
  cd backend && uvicorn main:app --reload --port 8001
  cd frontend && npm run dev
  cd backend && pytest -v

KEY FILES:
- backend/services/prompt_intelligence.py  # Prompt Intelligence v2
- backend/services/model_scorer.py           # Task-aware routing
- backend/routers/chat.py                    # /chat, /chat/stream, /chat/regenerate
- backend/services/chat_service.py           # Shared pipeline
- frontend/src/api/chat.js                   # streamChat()
- frontend/src/components/ChatPage.jsx
- frontend/src/components/PromptEnhancementViewer.jsx

GITHUB: https://github.com/Apatel468/TokenMaxx
CONSTRAINTS: Groq allowlist only, port 8001, never read/log .env
```
