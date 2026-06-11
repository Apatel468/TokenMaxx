# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Permanent project context.** This file is the single source of truth when chat history is unavailable.  
> **Version:** 0.3.1 · **Last audited:** June 2026  
> **GitHub:** https://github.com/Apatel468/TokenMaxx (redirects from `smartllm-router`)

---

## Project Vision

**TokenMaxx** — *Maximum Intelligence, Minimum Cost* — is an enterprise-style demo/MVP that intelligently routes user prompts to the most cost-effective AI model while maintaining acceptable quality. It proves **task-aware model selection**, **prompt engineering**, **org-wide and per-user model toggles**, **JWT authentication**, **admin usage visibility**, and **cost savings tracking** compared to always using an expensive premium model (GPT-4o baseline).

The product narrative: *"Maximum Intelligence, Minimum Cost — classify the request, engineer the prompt, score every Groq model, route to the best enabled option for this user, and show how much you saved."*

---

## Business Problem Being Solved

Organizations and developers often default to one expensive LLM (e.g. GPT-4o) for every request. Many tasks do not need premium reasoning. TokenMaxx:

1. **Authenticates** users with JWT so chats and analytics are per-account
2. **Classifies** what kind of task the user is asking for (keyword rules; LLM classifier optional upgrade)
3. **Enhances** the prompt with task-specific structure (AI agent or rule fallback)
4. **Scores** all routable Groq models using registry metadata + task profile weights
5. **Routes** to the highest-scoring **available** model (`admin_enabled AND user_enabled`)
6. **Tracks** estimated token cost vs. a premium baseline
7. **Persists** conversations, titles, and analytics per user for audit and demo purposes
8. **Reports** employee usage to admins (cost, model breakdown)

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  React + Vite Frontend (localhost:5173 or 5174)                  │
│  Auth gate → Login / Signup                                        │
│  Tabs: Chat | Analytics | Model Controls | Admin (admins only)     │
│  JWT in localStorage (tokenmaxx_token) via api/http.js             │
└────────────────────────────┬─────────────────────────────────────┘
                             │ REST JSON + Authorization: Bearer
                             │ → http://127.0.0.1:8001
┌────────────────────────────▼─────────────────────────────────────┐
│  FastAPI Backend (127.0.0.1:8001)                                │
│  Public: /auth/* /health                                         │
│  Protected: /chat /conversations /analytics/* /models            │
│             /model-settings /admin/*                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
 auth_service           prompt_analyzer         router_engine
 (JWT + bcrypt)         prompt_enhancer         (model_scorer + registry)
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
              (users, conversations, messages, model_runs,
               admin_model_settings, user_model_settings)
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
| Auth | bcrypt, PyJWT (HS256 Bearer tokens) |
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
│   ├── database.py              # users, admin/user model settings, conversations
│   ├── models.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/
│   │   ├── models.yaml          # task_profiles, auxiliary models, baseline
│   │   └── model_registry.py    # Groq model metadata + scores (add models here)
│   ├── routers/
│   │   ├── auth.py              # signup, login, logout, me
│   │   ├── admin.py             # employee usage (admin only)
│   │   ├── model_settings_route.py  # GET/PUT /model-settings
│   │   ├── chat.py, conversations.py, analytics.py, models.py
│   │   └── settings.py          # legacy /settings/models aliases
│   ├── scripts/
│   │   └── cleanup_test_users.py
│   └── services/
│       ├── auth_service.py, auth_dependencies.py
│       ├── prompt_analyzer.py, prompt_enhancer.py, context_builder.py
│       ├── router_engine.py, model_scorer.py, groq_models.py
│       ├── model_settings.py    # admin + user preference overlay
│       ├── model_clients.py, response_cleaner.py, cost_tracker.py
│       ├── conversation_store.py, conversation_title.py
│       ├── report_generator.py, timezone_utils.py
│       └── config_loader.py
├── frontend/src/
│   ├── components/
│   │   ├── ChatPage.jsx, AnalyticsDashboard.jsx, ModelControls.jsx
│   │   ├── Login.jsx, Signup.jsx, AdminDashboard.jsx
│   ├── api/
│   │   ├── auth.js, http.js, admin.js, settings.js
│   │   ├── chat.js, conversations.js, analytics.js, config.js
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
| Model Controls — org + personal toggles | ✅ Complete (v0.3.1) |
| Unified GET/PUT `/model-settings` | ✅ Complete |
| JWT auth (signup/login/logout/me) | ✅ Complete (v0.3.1) |
| Per-user conversations & analytics | ✅ Complete |
| Admin employee usage dashboard | ✅ Complete |
| Keyword task classifier | ✅ Complete |
| LLM task classifier (Phase 3B) | ⚠️ Optional upgrade — not in code yet |
| AI prompt engineering agent | ✅ Complete |
| Mock fallback (no API key) | ✅ Complete |
| SQLite persistence | ✅ Complete |
| Multi-turn conversations + titles | ✅ Complete |
| Analytics API + dashboard | ✅ Complete |
| Frontend chat UI (3-column, routing score) | ✅ Complete |
| Frontend Model Controls tab | ✅ Complete |
| Frontend shows enhancement fields | ❌ Not started |
| Streaming responses | ❌ Not started |
| Tests | ❌ Not started |

---

## Authentication (v0.3.1)

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /auth/signup` | Public | Create account (`role` defaults to `user`) |
| `POST /auth/login` | Public | Returns JWT `access_token` |
| `POST /auth/logout` | Bearer | Client discards token (stateless JWT) |
| `GET /auth/me` | Bearer | Current user profile |

- Passwords hashed with **bcrypt**; tokens are **HS256 JWT** (`JWT_SECRET`, `JWT_EXPIRE_HOURS` in `.env`)
- Optional startup admin seed: `ADMIN_EMAIL` + `ADMIN_PASSWORD` in `.env`
- Frontend stores token in `localStorage` key `tokenmaxx_token`; `api/http.js` → `authFetch()` attaches `Authorization: Bearer`
- All chat, analytics, conversations, models, and model-settings routes require a valid token

---

## Model Controls (v0.3.1)

**Effective availability:** `available = admin_enabled AND user_enabled` (missing DB rows default to `enabled=true`).

| Who | Saves | DB table | Effect |
|-----|-------|----------|--------|
| Admin | `admin_enabled` | `admin_model_settings` | Org-wide on/off; users see "Disabled by admin" |
| User | `user_enabled` | `user_model_settings` | Personal preference on top of admin |

**Primary API:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/model-settings` | All routable models + `admin_enabled`, `user_enabled`, `available` |
| PUT | `/model-settings` | UPSERT toggles (admin → org, user → personal) |

**Legacy aliases:** `GET/PUT /settings/models` (same logic).

Router (`router_engine.py`) filters to **available** models for the requesting `user_id`.

---

## Routing (v0.3.0+)

Model selection is **dynamic** — not a fixed 3-model YAML map.

1. `groq_models.sync_groq_catalog()` — merges Groq API list with `model_registry.py`
2. Filter to user-**available** models (`admin_model_settings` ∩ `user_model_settings`)
3. `model_scorer.score_candidates()` for the detected `task_type`:

```
score = (task_match × 0.4) + (cost_efficiency × 0.2)
      + (speed_score × 0.2) + (reasoning_score × 0.2)
```

4. Pick highest score; if top model is unavailable, use next available (fallback badge in UI)
5. Return `routing_score` + `candidate_models[]` in `POST /chat` response

**To add a new Groq model:** edit `backend/config/model_registry.py` only — no router code changes.

---

## POST /chat Pipeline (Current)

```
1. Require JWT → resolve user_id
2. Load prior messages (optional conversation_id, scoped to user)
3. prompt_analyzer.analyze_prompt()
4. context_builder.build_context()      → prompt_enhancer.enhance_prompt()
5. router_engine.route(context, db, user_id)   → score all available Groq models
6. model_clients.generate_response()
7. response_cleaner.clean_model_response()
8. cost_tracker.estimate_costs() + log_request_metrics()
9. conversation_store.save_chat_turn(user_id=...)
10. ChatResponse JSON (includes routing_score, candidate_models)
```

---

## API Endpoints (Quick Reference)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | — | Liveness check |
| POST | `/auth/signup` | — | Register |
| POST | `/auth/login` | — | Login → JWT |
| POST | `/auth/logout` | Bearer | Logout |
| GET | `/auth/me` | Bearer | Current user |
| POST | `/chat` | Bearer | Full pipeline; optional `conversation_id` |
| GET | `/conversations` | Bearer | List summaries (own threads) |
| GET | `/conversations/{id}` | Bearer | Full thread |
| GET | `/analytics/summary` | Bearer | Aggregate cost/savings |
| GET | `/analytics/history` | Bearer | Per-run history |
| GET | `/analytics/model-usage` | Bearer | Per-model stats |
| GET | `/models` | Bearer | Routable catalog from registry |
| GET | `/models/sync` | Bearer | Force Groq API sync + registry gap report |
| GET | `/model-settings` | Bearer | Model Controls list |
| PUT | `/model-settings` | Bearer | Save model toggles |
| GET | `/settings/models` | Bearer | Legacy alias for model-settings |
| PUT | `/settings/models` | Bearer | Legacy alias for model-settings |
| GET | `/admin/employee-usage` | Admin | Per-user cost & model breakdown |
| GET | `/docs` | — | Swagger UI |

### POST /chat Response Fields (key)

| Field | Description |
|-------|-------------|
| `selected_model` | e.g. `Groq / openai/gpt-oss-20b` |
| `routing_score` | Composite 0–100 score for chosen model |
| `candidate_models` | All scored models with breakdown |
| `preferred_model` | Top scorer before enable/disable rules |
| `used_fallback` / `fallback_message` | When preferred model is unavailable |
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
| `JWT_SECRET` | Recommended | HS256 signing key (change in production) |
| `JWT_EXPIRE_HOURS` | Optional | Token lifetime (default 168 = 7 days) |
| `ADMIN_EMAIL` | Optional | Seed/promote admin on startup |
| `ADMIN_PASSWORD` | Optional | Admin seed password (min 8 chars) |

\*Without `GROQ_API_KEY`: keyword classify, rule enhance/title, mock responses, registry-only catalog.

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
| Health | http://127.0.0.1:8001/health |

**Windows restart tip:** If `/model-settings` returns 404 after code changes, orphaned uvicorn worker processes may still hold port 8001. Kill all `python.exe` processes tied to uvicorn, then start fresh.

---

## Known Bugs & Technical Debt

- LLM classifier not implemented — keyword only
- Registry scores are editorial estimates, not live benchmarks
- `ChatResponse.mock_response` legacy field name
- No automated tests
- No Alembic migrations (tables created/migrated in `init_db()`)
- JWT is stateless — no server-side revoke list

---

## Recommended Next Steps

1. Tune registry scores from real usage / benchmarks
2. Frontend — show original vs enhanced prompt in Chat UI
3. Context truncation for long threads
4. pytest for `model_scorer`, routing, and auth
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
- backend/config/model_registry.py        # add new Groq models here
- backend/services/model_scorer.py        # routing formula
- backend/services/router_engine.py       # passes user_id for available models
- backend/services/model_settings.py      # admin + user model toggles
- backend/routers/model_settings_route.py # GET/PUT /model-settings
- backend/services/auth_service.py        # JWT + bcrypt
- frontend/src/api/settings.js            # Model Controls API client
- frontend/src/components/ModelControls.jsx

GITHUB: https://github.com/Apatel468/TokenMaxx
CONSTRAINTS: Groq-only, port 8001, never read/log .env
```
