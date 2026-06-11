# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.3.1 · **Last updated:** June 2026

---

## System Architecture

| Tier | Role |
|------|------|
| **Presentation** | React SPA (Vite, port 5173 or 5174) — Login/Signup, Chat, Analytics, Model Controls, Admin |
| **Application** | FastAPI monolith (port 8001) — JWT auth middleware via `Depends(get_current_user)` |
| **Data** | SQLite (`smartllm_router.db`) |
| **External** | Groq API via LiteLLM + `GET /openai/v1/models` for catalog sync |

---

## Backend Service Layer

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| `auth_service` | email/password | JWT, User | bcrypt hash; optional admin seed |
| `auth_dependencies` | Bearer header | User | `get_current_user`, `require_admin` |
| `prompt_analyzer` | prompt | `AnalysisResult` | Keyword classify |
| `prompt_enhancer` | prompt + metadata | `EnhancementResult` | Groq AI JSON; rule fallback |
| `context_builder` | prompt + analysis + history | `PromptContext` | Builds `message_history` |
| `groq_models` | — | `GroqModelRecord[]` | API + registry merge; logs missing models |
| `model_scorer` | task_type + candidates | `CandidateScore[]` | Composite routing formula |
| `router_engine` | `PromptContext` + DB + `user_id` | `RoutingDecision` | Picks best available model |
| `model_settings` | DB + user_id | admin/user/available flags | Two-tier enable/disable |
| `config_loader` | — | YAML dict | Task profiles, auxiliary models |
| `model_clients` | model + context | `ModelResponse` | LiteLLM; mock fallback |
| `cost_tracker` | model + response | `CostEstimate` | Registry pricing vs GPT-4o |
| `conversation_store` | turn data + user_id | `(id, title)` | Per-user thread persistence |
| `report_generator` | DB | employee usage rows | Admin analytics |
| `timezone_utils` | UTC datetime | Eastern display string | API timestamps |

---

## POST /chat Data Flow

```
Client → POST /chat { prompt, conversation_id? }  [Authorization: Bearer]
  → get_current_user() → user_id
  → load_message_history(user_id)
  → analyze_prompt()           # keyword → task_type
  → build_context()            # enhance_prompt()
  → route(context, db, user_id)  # score all available Groq models
  → generate_response()        # LiteLLM
  → clean_model_response()
  → estimate_costs()
  → save_chat_turn(user_id=...)
  → ChatResponse (+ routing_score, candidate_models)
```

---

## Dynamic Model Routing

### Configuration split

| File / Table | Purpose |
|--------------|---------|
| `config/model_registry.py` | Per-model metadata: scores, cost, latency, strengths |
| `config/models.yaml` | Task profiles (capability weights), auxiliary models, premium baseline |
| SQLite `admin_model_settings` | Org-wide enable/disable per model id |
| SQLite `user_model_settings` | Per-user enable/disable per model id |

**Available for routing:** `admin_enabled AND user_enabled` (missing rows default to enabled).

### Scoring formula (`model_scorer.py`)

```
score = (task_match × 0.4) + (cost_efficiency × 0.2)
      + (speed_score × 0.2) + (reasoning_score × 0.2)
```

- **task_match** — weighted blend of `coding_score`, `writing_score`, `reasoning_score` from registry, using `task_profiles` in YAML
- **cost_efficiency** / **speed_score** — normalized relative to all routable candidates (cheaper/faster → higher)
- **reasoning_score** — direct from registry (0–100)

### RoutingDecision (extended)

```python
@dataclass
class RoutingDecision:
    model_id: str
    model_label: str
    groq_model: str
    score: float
    candidate_models: list[dict]
    preferred_model_id: str
    used_fallback: bool
    fallback_message: str
```

---

## Model Controls API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/model-settings` | Bearer | List routable models + admin/user/available flags |
| PUT | `/model-settings` | Bearer | UPSERT toggles (role-aware) |
| GET | `/settings/models` | Bearer | Legacy alias |
| PUT | `/settings/models` | Bearer | Legacy alias |

Admins write `admin_enabled`; regular users write `user_enabled` only. Admin-disabled models show as locked in the UI.

---

## Auth API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/signup` | — | Register (`role=user`) |
| POST | `/auth/login` | — | JWT access token |
| POST | `/auth/logout` | Bearer | Stateless logout |
| GET | `/auth/me` | Bearer | Profile |
| GET | `/admin/employee-usage` | Admin | Per-user usage metrics |

---

## Cost Tracking (`cost_tracker.py`)

- Rates from `model_registry.py` via `cost_per_1k_tokens()`
- Baseline from `models.yaml` → `premium_baseline`

---

## Frontend

| Screen / Tab | Component | Notes |
|--------------|-----------|-------|
| Login / Signup | `Login.jsx`, `Signup.jsx` | Auth gate before main app |
| Chat | `ChatPage.jsx` | 3-column; routing score + top candidates |
| Analytics | `AnalyticsDashboard.jsx` | KPIs, model table, history |
| Model Controls | `ModelControls.jsx` | Admin org toggles or user personal toggles |
| Admin | `AdminDashboard.jsx` | Employee usage (admin role only) |

**HTTP layer:** `api/http.js` — `authFetch()` attaches JWT from `localStorage` (`tokenmaxx_token`).

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `users` | Accounts: email, hashed_password, role (`user` \| `admin`) |
| `conversations` | Thread metadata + title + `user_id` |
| `messages` | User/assistant content |
| `model_runs` | Routing, tokens, costs per reply + `user_id` |
| `admin_model_settings` | Org-wide `model_id` + `enabled` |
| `user_model_settings` | Per-user `model_id` + `enabled` |

Legacy `model_settings` table migrated to `admin_model_settings` on startup if present.
