# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Permanent project context.** This file is the single source of truth when chat history is unavailable.  
> **Version:** 0.3.2 · **Last audited:** June 2026  
> **GitHub:** https://github.com/Apatel468/TokenMaxx (redirects from `smartllm-router`)

---

## Project Vision

**TokenMaxx** — *Maximum Intelligence, Minimum Cost* — is an enterprise-style demo/MVP that intelligently routes user prompts to the most cost-effective AI model while maintaining acceptable quality. It proves **task-aware model selection**, **optional prompt engineering**, **org-wide and per-user model toggles**, **on-demand model regeneration**, **JWT authentication**, **admin usage visibility**, and **cost savings tracking** compared to always using an expensive premium model (GPT-4o baseline).

The product narrative: *"Maximum Intelligence, Minimum Cost — classify the request, optionally engineer the prompt, score allowed Groq models, route to the best enabled option for this user, let them retry with another model on demand, and show how much you saved."*

---

## Business Problem Being Solved

Organizations and developers often default to one expensive LLM (e.g. GPT-4o) for every request. Many tasks do not need premium reasoning. TokenMaxx:

1. **Authenticates** users with JWT so chats and analytics are per-account
2. **Classifies** what kind of task the user is asking for (keyword rules)
3. **Optionally enhances** the prompt (user toggle; AI agent or rule fallback)
4. **Scores** allowlisted Groq chat models using registry metadata + task profile weights
5. **Routes** to the highest-scoring **available** model (`admin_enabled AND user_enabled`)
6. **Lets users regenerate** with any other allowed model — one LLM call per click, no upfront multi-model cost
7. **Tracks** estimated token cost vs. a premium baseline
8. **Persists** conversations, titles, and analytics per user
9. **Reports** employee usage to admins

---

## Groq Model Allowlist (v0.3.2)

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

Historical `model_runs` with removed model ids remain in analytics unchanged.

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
│  Protected: /chat /chat/regenerate /conversations /analytics/*   │
│             /models /model-settings /user/preferences /admin/*   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
 auth_service           prompt_analyzer         router_engine
 user_preferences       prompt_enhancer         (allowlist + scorer)
 regenerate_service     context_builder
     │                       │                       │
     └──────────► model_clients (LiteLLM → Groq) ◄──┘
                             │
              cost_tracker + conversation_store
                             │
                             ▼
              SQLite: smartllm_router.db
```

**Per chat request with `GROQ_API_KEY` and enhancement ON:**
- **First turn:** up to **3 Groq calls** — enhancer, response model, title
- **Follow-up turns:** up to **2 Groq calls** — enhancer, response model
- **Enhancement OFF:** skips enhancer call (saves cost/latency)
- **Regenerate click:** **1 Groq call only** — reuses stored prompts; no re-classify/route

---

## Technologies Used

| Layer | Technology |
|-------|------------|
| Backend API | Python 3, FastAPI 0.109+ |
| Server | Uvicorn |
| ORM / DB | SQLAlchemy 2.x, SQLite |
| Auth | bcrypt, PyJWT (HS256 Bearer tokens) |
| LLM gateway | LiteLLM 1.40+ |
| LLM provider | Groq (allowlisted models only) |
| Config | YAML (`config/models.yaml`), Python registry (`config/model_registry.py`) |
| Frontend | React 18, Vite 6 |
| Styling | Plain CSS |

---

## Folder Structure

```
smartllm-router/
├── backend/
│   ├── config/
│   │   ├── models.yaml
│   │   └── model_registry.py      # GROQ_MODEL_ALLOWLIST + metadata
│   ├── routers/
│   │   ├── auth.py, admin.py, chat.py
│   │   ├── model_settings_route.py, user_preferences.py
│   │   └── conversations.py, analytics.py, models.py, settings.py
│   └── services/
│       ├── auth_service.py, user_preferences.py
│       ├── regenerate_service.py, recommendations.py
│       ├── router_engine.py, model_scorer.py, groq_models.py
│       ├── model_settings.py, context_builder.py, conversation_store.py
│       └── ...
├── frontend/src/
│   ├── components/ ChatPage, AnalyticsDashboard, ModelControls, ...
│   └── api/ chat.js, preferences.js, settings.js, ...
└── docs/
```

---

## Current Implementation Status

| Area | Status |
|------|--------|
| Backend core pipeline | ✅ Complete |
| Groq allowlist (6 chat models) | ✅ Complete (v0.3.2) |
| Dynamic scoring router | ✅ Complete |
| Model Controls — org + personal toggles | ✅ Complete |
| JWT auth + admin dashboard | ✅ Complete |
| User prompt enhancement toggle | ✅ Complete (v0.3.2) |
| Model regenerate (on-demand) | ✅ Complete (v0.3.2) |
| Top-5 recommendations in routing panel | ✅ Complete |
| Analytics (cost, savings, model usage) | ✅ Complete |
| LLM task classifier | ⚠️ Not implemented |
| Streaming responses | ❌ Not started |
| Tests | ❌ Not started |

---

## User Preferences (v0.3.2)

| Setting | Default | API |
|---------|---------|-----|
| `enhance_prompts` | `true` | `GET/PUT /user/preferences` |

Also returned on `GET /auth/me` as `enhance_prompts`. Toggle in **Model Controls** tab; saves immediately. When off, `POST /chat` sends `enhance_prompt: false` and skips `enhance_prompt()`.

---

## Model Regenerate (v0.3.2)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat/regenerate` | Retry a turn with user-selected model |

**Request:** `{ conversation_id, message_id, model_id }` — `message_id` is the **user message** for that turn.

**Behavior:**
- Reuses stored enhanced prompt, system prompt, and conversation context
- Does **not** re-classify, re-enhance, or re-route
- **One LLM call per click** — no pre-generation of all top-5 models
- Appends new assistant message; original router response kept
- UI: `User switched model to "{model_id}"` above regenerated text
- Router-selected replies labeled **Router Selected**

`POST /chat` returns `top_recommendations` (top 5 with cost/latency estimates and availability) for clickable chips in the routing panel.

---

## Model Controls (v0.3.1+)

**Effective availability:** `available = admin_enabled AND user_enabled`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/model-settings` | All allowlisted chat models + toggle state |
| PUT | `/model-settings` | UPSERT toggles (admin → org, user → personal) |

Also includes **Prompt Enhancement** toggle (user preference).

---

## Routing (v0.3.0+)

1. Load allowlisted chat models from `groq_models.get_routable_models()`
2. Filter to user-available models (admin ∩ user prefs)
3. Score with composite formula (task_match 40%, cost 20%, speed 20%, reasoning 20%)
4. Pick highest score; fallback if preferred unavailable
5. Return `top_recommendations` (top 5) + `routing_score`

---

## POST /chat Pipeline

```
1. JWT → user_id
2. Load prior messages (optional conversation_id)
3. analyze_prompt() — keyword classify
4. build_context(enhance_prompt_enabled=request.enhance_prompt)
5. route(context, db, user_id) — score allowlisted available models
6. generate_response()
7. estimate_costs() + save_chat_turn (label: "Router Selected")
8. ChatResponse + top_recommendations + user_message_id
```

---

## API Endpoints (Quick Reference)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | — | Liveness |
| POST | `/auth/signup` | — | Register |
| POST | `/auth/login` | — | Login → JWT |
| GET | `/auth/me` | Bearer | Profile + `enhance_prompts` |
| GET | `/user/preferences` | Bearer | User settings |
| PUT | `/user/preferences` | Bearer | Save settings |
| POST | `/chat` | Bearer | Full pipeline; `enhance_prompt` optional |
| POST | `/chat/regenerate` | Bearer | User-selected model retry |
| GET | `/conversations` | Bearer | List threads |
| GET | `/conversations/{id}` | Bearer | Full thread + `selected_model` on regen msgs |
| GET | `/analytics/summary` | Bearer | Cost/savings KPIs |
| GET | `/analytics/history` | Bearer | Recent runs |
| GET | `/analytics/model-usage` | Bearer | Per-model stats |
| GET | `/model-settings` | Bearer | Model Controls |
| PUT | `/model-settings` | Bearer | Save model toggles |
| GET | `/admin/employee-usage` | Admin | Org-wide usage |
| GET | `/docs` | — | Swagger UI |

### Analytics UI (displayed)

Total Chats, Actual Cost, Premium Cost, Total Savings, Savings %, Model Usage table, Recent Conversations.

Enhancement/regeneration metrics are tracked in DB but **not shown** in the dashboard UI.

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Optional* | Chat, enhancer, title, catalog sync |
| `JWT_SECRET` | Recommended | HS256 signing key |
| `JWT_EXPIRE_HOURS` | Optional | Token lifetime (default 168) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Optional | Seed admin on startup |

---

## How to Run

```bash
cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 8001
cd frontend && npm run dev
```

| What | URL |
|------|-----|
| App | http://localhost:5173 |
| API docs | http://127.0.0.1:8001/docs |

**Windows restart tip:** Kill orphaned uvicorn workers if `/model-settings` returns 404 after code changes.

---

## Known Bugs & Technical Debt

- LLM classifier not implemented
- Registry scores are editorial estimates
- `ChatResponse.mock_response` legacy field name
- No automated tests; no Alembic migrations
- JWT stateless — no server-side revoke

---

# CURSOR HANDOFF PROMPT

```
You are continuing development on TokenMaxx — Maximum Intelligence, Minimum Cost.

READ FIRST: docs/project_memory.md, architecture.md, system_design.md

RUN:
  cd backend && uvicorn main:app --reload --port 8001
  cd frontend && npm run dev

KEY FILES:
- backend/config/model_registry.py     # GROQ_MODEL_ALLOWLIST
- backend/services/router_engine.py
- backend/services/regenerate_service.py
- backend/services/user_preferences.py
- backend/routers/chat.py
- frontend/src/components/ChatPage.jsx
- frontend/src/components/ModelControls.jsx

GITHUB: https://github.com/Apatel468/TokenMaxx
CONSTRAINTS: Groq allowlist only, port 8001, never read/log .env
```
