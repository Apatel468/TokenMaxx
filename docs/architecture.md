# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.3.2 · **Last updated:** June 2026

---

## System Architecture

| Tier | Role |
|------|------|
| **Presentation** | React SPA — Login, Chat (regenerate chips), Analytics, Model Controls, Admin |
| **Application** | FastAPI monolith — JWT via `Depends(get_current_user)` |
| **Data** | SQLite (`smartllm_router.db`) |
| **External** | Groq API via LiteLLM (allowlisted models only) |

---

## Backend Service Layer

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| `auth_service` | credentials | JWT, User | bcrypt; admin seed |
| `user_preferences` | user_id | `enhance_prompts` | SQLite `user_preferences` |
| `prompt_analyzer` | prompt | `AnalysisResult` | Keyword classify |
| `context_builder` | prompt + flags | `PromptContext` | Skips enhance when disabled |
| `prompt_enhancer` | prompt + metadata | `EnhancementResult` | Groq AI or rules |
| `groq_models` | — | `GroqModelRecord[]` | Allowlist-only catalog |
| `model_scorer` | task_type + candidates | `CandidateScore[]` | Composite formula |
| `router_engine` | context + DB + user | `RoutingDecision` | Best available model |
| `recommendations` | scores + context | top-5 metadata | No LLM calls |
| `regenerate_service` | turn + model_id | new assistant msg | Reuses stored prompts |
| `model_settings` | DB + user_id | availability flags | Two-tier toggles + cleanup |
| `model_clients` | model + context | `ModelResponse` | LiteLLM |
| `conversation_store` | turn data | ids, labels | Router / regen labels |
| `report_generator` | DB | analytics rows | Per-user + admin |

---

## POST /chat Data Flow

```
Client → POST /chat { prompt, conversation_id?, enhance_prompt? }
  → authenticate → classify → build_context (optional enhance)
  → route (allowlisted + available models)
  → generate_response → save ("Router Selected")
  → ChatResponse + top_recommendations[5]
```

## POST /chat/regenerate Data Flow

```
Client → POST /chat/regenerate { conversation_id, message_id, model_id }
  → load turn context from model_runs (no classify/enhance/route)
  → check model availability (Model Controls)
  → generate_response(selected model)
  → append assistant message ("User Selected Model")
  → new model_run (is_regeneration=true)
```

---

## Groq Allowlist

Defined in `config/model_registry.py`:

- **Chat (6):** llama-3.1-8b-instant, llama-3.3-70b-versatile, llama-4-scout, qwen3-32b, gpt-oss-20b, gpt-oss-120b
- **Audio (1):** whisper-large-v3 — not routable for chat

`groq_models.py` builds catalog from allowlist only; API is used for availability flags, not to add models.

---

## Scoring Formula

```
score = (task_match × 0.4) + (cost_efficiency × 0.2)
      + (speed_score × 0.2) + (reasoning_score × 0.2)
```

---

## API Summary

| Area | Endpoints |
|------|-----------|
| Auth | `/auth/signup`, `/auth/login`, `/auth/me` |
| Chat | `POST /chat`, `POST /chat/regenerate` |
| Preferences | `GET/PUT /user/preferences` |
| Model Controls | `GET/PUT /model-settings` |
| Analytics | `/analytics/summary`, `/history`, `/model-usage` |
| Admin | `GET /admin/employee-usage` |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `users` | Accounts + role |
| `user_preferences` | `enhance_prompts` per user |
| `conversations` | Threads + title + `user_id` |
| `messages` | Content + `response_label` (Router Selected / User Selected Model) |
| `model_runs` | Costs, tokens, enhancement + regeneration metadata |
| `admin_model_settings` | Org-wide model toggles |
| `user_model_settings` | Per-user model toggles |

`model_runs` fields for regeneration: `is_regeneration`, `original_model`, `regenerated_model`, `turn_user_message_id`.

---

## Frontend

| Component | Responsibility |
|-----------|----------------|
| `ChatPage.jsx` | Thread, routing panel, top-5 regenerate chips, model-switch labels |
| `ModelControls.jsx` | Model toggles + Prompt Enhancement toggle |
| `AnalyticsDashboard.jsx` | Cost/savings KPIs, model table, history (no enhancement KPIs) |
| `AdminDashboard.jsx` | Employee usage |
