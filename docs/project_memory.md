# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Permanent project context.** This file is the single source of truth when chat history is unavailable.  
> **Version:** 0.3.0 · **Last audited:** June 2026  
> **GitHub:** https://github.com/Apatel468/smartllm-router

---

## Project Vision

**TokenMaxx** — *Maximum Intelligence, Minimum Cost* — is an enterprise-style demo/MVP that intelligently routes user prompts to the most cost-effective AI model while maintaining acceptable quality. It proves **task-aware model selection**, **prompt engineering**, **user-controlled model toggles**, and **cost savings tracking** compared to always using an expensive premium model (GPT-4o baseline).

The product narrative: *"Maximum Intelligence, Minimum Cost — classify the request, engineer the prompt, score every Groq model, route to the best enabled option, and show how much you saved."*

---

## Business Problem Being Solved

Organizations and developers often default to one expensive LLM (e.g. GPT-4o) for every request. Many tasks do not need premium reasoning. TokenMaxx:

1. **Classifies** what kind of task the user is asking for (keyword rules; LLM classifier optional upgrade)
2. **Enhances** the prompt with task-specific structure (AI agent or rule fallback)
3. **Scores** all routable Groq models using registry metadata + task profile weights
4. **Routes** to the highest-scoring **enabled** model (Model Controls in SQLite)
5. **Tracks** estimated token cost vs. a premium baseline
6. **Persists** conversations, titles, and analytics for audit and demo purposes

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  React + Vite Frontend (localhost:5173 or 5174)                    │
│  Tabs: Chat (3-column) | Analytics | Model Controls               │
└────────────────────────────┬─────────────────────────────────────┘
                             │ REST JSON → http://127.0.0.1:8001
┌────────────────────────────▼─────────────────────────────────────┐
│  FastAPI Backend (127.0.0.1:8001)                                │
│  Routers: /chat /conversations /analytics/* /models /settings    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
 prompt_analyzer      prompt_enhancer         router_engine
 (keyword classify)   (Groq AI agent + rules) (model_scorer + registry)
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
              (conversations, messages, model_runs, model_settings)
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
| Config | YAML (`config/models.yaml`), Python registry (`config/model_registry.py`), python-dotenv |
| Frontend | React 18, Vite 6 |
| Styling | Plain CSS (no Tailwind/UI library) |

---

## Folder Structure

```
smartllm-router/
├── backend/
│   ├── main.py
│   ├── database.py              # + model_settings table
│   ├── models.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/
│   │   ├── models.yaml          # task_profiles, auxiliary models, baseline
│   │   └── model_registry.py    # Groq model metadata + scores (add models here)
│   ├── routers/ (chat, conversations, analytics, models, settings)
│   └── services/
│       ├── prompt_analyzer.py
│       ├── prompt_enhancer.py
│       ├── context_builder.py
│       ├── router_engine.py     # dynamic scoring router
│       ├── model_scorer.py      # composite score formula
│       ├── groq_models.py       # Groq API catalog sync
│       ├── model_settings.py    # enable/disable preferences
│       ├── config_loader.py
│       ├── model_clients.py
│       ├── response_cleaner.py
│       ├── cost_tracker.py
│       ├── conversation_store.py
│       ├── conversation_title.py
│       └── report_generator.py
├── frontend/src/
│   ├── components/ (ChatPage, AnalyticsDashboard, ModelControls)
│   ├── api/ (chat, conversations, analytics, settings, config.js)
│   └── utils/conversationTitle.js
└── docs/
```

---

## Current Implementation Status

| Area | Status |
|------|--------|
| Backend core pipeline | ✅ Complete |
| Groq + LiteLLM integration | ✅ Complete |
| Dynamic scoring router (all Groq models) | ✅ Complete (v0.3.0) |
| Model registry + Groq API sync | ✅ Complete |
| Model Controls (enable/disable) | ✅ Complete |
| Keyword task classifier | ✅ Complete |
| LLM task classifier (Phase 3B) | ⚠️ Optional upgrade — not in code yet |
| AI prompt engineering agent | ✅ Complete |
| Mock fallback (no API key) | ✅ Complete |
| SQLite persistence | ✅ Complete |
| Multi-turn conversations + titles | ✅ Complete |
| Analytics API + dashboard | ✅ Complete |
| Analytics layout (no horizontal scroll) | ✅ Complete |
| Frontend chat UI (3-column, routing score) | ✅ Complete |
| Frontend Model Controls tab | ✅ Complete |
| Frontend shows enhancement fields | ❌ Not started |
| Auth / multi-user | ❌ Not started |
| Streaming responses | ❌ Not started |
| Tests | ❌ Not started |

---

## Routing (v0.3.0)

Model selection is **dynamic** — not a fixed 3-model YAML map.

1. `groq_models.sync_groq_catalog()` — merges Groq API list with `model_registry.py`
2. Filter to user-**enabled** models (`model_settings` SQLite table)
3. `model_scorer.score_candidates()` for the detected `task_type`:

```
score = (task_match × 0.4) + (cost_efficiency × 0.2)
      + (speed_score × 0.2) + (reasoning_score × 0.2)
```

4. Pick highest score; if top model is disabled, use next enabled (fallback badge in UI)
5. Return `routing_score` + `candidate_models[]` in `POST /chat` response

**To add a new Groq model:** edit `backend/config/model_registry.py` only — no router code changes.

---

## POST /chat Pipeline (Current)

```
1. Load prior messages (optional conversation_id)
2. prompt_analyzer.analyze_prompt()
3. context_builder.build_context()      → prompt_enhancer.enhance_prompt()
4. router_engine.route(context, db)   → score all enabled Groq models
5. model_clients.generate_response()
6. response_cleaner.clean_model_response()
7. cost_tracker.estimate_costs() + log_request_metrics()
8. conversation_store.save_chat_turn()
9. ChatResponse JSON (includes routing_score, candidate_models)
```

---

## API Endpoints (Quick Reference)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check |
| POST | `/chat` | Full pipeline; optional `conversation_id` |
| GET | `/conversations` | List summaries |
| GET | `/conversations/{id}` | Full thread |
| GET | `/analytics/summary` | Aggregate cost/savings |
| GET | `/analytics/history` | Per-run history |
| GET | `/analytics/model-usage` | Per-model stats |
| GET | `/models` | Routable catalog from registry |
| GET | `/models/sync` | Force Groq API sync + registry gap report |
| GET | `/settings/models` | Model Controls list |
| PUT | `/settings/models` | Save enable/disable toggles |
| GET | `/docs` | Swagger UI |

### POST /chat Response Fields (key)

| Field | Description |
|-------|-------------|
| `selected_model` | e.g. `Groq / openai/gpt-oss-20b` |
| `routing_score` | Composite 0–100 score for chosen model |
| `candidate_models` | All scored models with breakdown |
| `preferred_model` | Top scorer before enable/disable rules |
| `used_fallback` / `fallback_message` | When preferred model is disabled |
| `mock_response` | Response text (legacy field name) |

---

## Groq Models

| Role | Model | Config location |
|------|-------|-----------------|
| Prompt engineer | `llama-3.1-8b-instant` | `models.yaml` → `auxiliary.enhancer` |
| Conversation title | `llama-3.1-8b-instant` | `models.yaml` → `auxiliary.title` |
| Chat response | Scored from registry | `router_engine` + `model_registry.py` |
| Savings baseline | GPT-4o rates | `models.yaml` → `premium_baseline` |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Optional* | Enhancer, title, chat, Groq catalog sync |

\*Without it: keyword classify, rule enhance/title, mock responses, registry-only catalog.

---

## How to Run

```bash
# Terminal 1 — Backend
cd backend && venv\Scripts\activate
uvicorn main:app --reload --port 8001

# Terminal 2 — Frontend
cd frontend && npm run dev
```

| What | URL |
|------|-----|
| App | http://localhost:5173 (or **5174**) |
| API docs | http://127.0.0.1:8001/docs |

---

## Known Bugs & Technical Debt

- LLM classifier not implemented — keyword only
- Registry scores are editorial estimates, not live benchmarks
- `ChatResponse.mock_response` legacy field name
- No automated tests
- No Alembic migrations

---

## Recommended Next Steps

1. Tune registry scores from real usage / benchmarks
2. Frontend — show original vs enhanced prompt in Chat UI
3. Context truncation for long threads
4. pytest for `model_scorer` and routing
5. SSE streaming responses

---

# CURSOR HANDOFF PROMPT

```
You are continuing development on TokenMaxx — Maximum Intelligence, Minimum Cost.

READ FIRST: docs/project_memory.md, architecture.md, system_design.md

RUN:
  cd backend && uvicorn main:app --reload --port 8001
  cd frontend && npm run dev

KEY FILES:
- backend/config/model_registry.py   # add new Groq models here
- backend/services/model_scorer.py   # routing formula
- backend/services/router_engine.py
- backend/services/model_settings.py # Model Controls
- backend/config/models.yaml         # task_profiles (not per-model routes)
- frontend/src/components/ModelControls.jsx

GITHUB: https://github.com/Apatel468/smartllm-router
CONSTRAINTS: Groq-only, port 8001, never read/log .env
```
