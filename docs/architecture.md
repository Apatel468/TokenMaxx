# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.3.3 · **Last updated:** June 2026

---

## System Architecture

| Tier | Role |
|------|------|
| **Presentation** | React SPA — Login, Chat (routing debug panel, regenerate chips), Analytics (CSV export), Model Controls, Admin |
| **Application** | FastAPI monolith — JWT via `Depends(get_current_user)` |
| **Data** | SQLite (`smartllm_router.db`) |
| **External** | Groq API via LiteLLM (allowlisted models only) |

---

## Backend Service Layer

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| `auth_service` | credentials | JWT, User | bcrypt; admin seed |
| `user_preferences` | user_id | `enhance_prompts` | SQLite `user_preferences` |
| `llm_classifier` | prompt | task_type, confidence, reason | Groq llama-3.1-8b-instant |
| `prompt_analyzer` | prompt | `AnalysisResult` | LLM first, keyword fallback |
| `context_builder` | prompt + flags | `PromptContext` | Skips enhance when disabled |
| `prompt_enhancer` | prompt + metadata | `EnhancementResult` | Groq AI or rules |
| `groq_models` | — | `GroqModelRecord[]` | Allowlist-only catalog |
| `model_scorer` | task_type + candidates + prompt | `CandidateScore[]` | Complexity-aware weights + task bonuses |
| `router_engine` | context + DB + user | `RoutingDecision` | Best available model |
| `recommendations` | scores + context | top-5 metadata | No LLM calls |
| `regenerate_service` | turn + model_id | new assistant msg | Reuses stored prompts |
| `model_settings` | DB + user_id | availability flags | Two-tier toggles + `explicitly_set` sync |
| `model_clients` | model + context | `ModelResponse` | LiteLLM |
| `conversation_store` | turn data | ids, labels | Router / regen labels |
| `report_generator` | DB | analytics rows | Per-user + admin |

---

## POST /chat Data Flow

```
Client → POST /chat { prompt, conversation_id?, enhance_prompt? }
  → authenticate
  → analyze_prompt (LLM classify → keyword fallback)
  → build_context (optional enhance)
  → route (complexity-aware score of allowlisted + available models)
  → generate_response → save ("Router Selected")
  → ChatResponse + top_recommendations[5] + top_candidate_scores[3]
     + classification_confidence + classification_reason
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

## Scoring Formula (v0.3.3)

Task-aware composite score with dynamic weights based on prompt complexity (0–1):

```
complexity = f(prompt_length, task_type, complexity_keywords)

weights = dynamic(complexity)   # cost/speed ↓ as complexity ↑

composite = task_match × w_task
          + cost_efficiency × w_cost
          + speed_score × w_speed
          + reasoning_score × w_reasoning
          + task_preference_bonus
```

**Task preference bonuses** (`TASK_MODEL_BONUSES` in `model_scorer.py`) steer routing per task type. Example: `coding` → `qwen/qwen3-32b` +16; `reasoning` → `openai/gpt-oss-120b` +14.

**Why gpt-oss-20b no longer dominates:** the old fixed 40% cost+speed weight favored the cheapest/fastest model on every prompt. Complexity-aware weights and task bonuses prioritize capability for hard tasks while still favoring `llama-3.1-8b-instant` for simple Q&A.

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
| `model_runs` | Costs, tokens, enhancement + regeneration + classification metadata |
| `admin_model_settings` | Org-wide model toggles |
| `user_model_settings` | Per-user model toggles (`explicitly_set` flag) |

`model_runs` fields for regeneration: `is_regeneration`, `original_model`, `regenerated_model`, `turn_user_message_id`.

`model_runs` fields for classification: `classification_reason`, `classification_confidence`.

---

## Frontend

| Component | Responsibility |
|-----------|----------------|
| `ChatPage.jsx` | Thread, Latest Routing panel (task, confidence, top-3 scores, reason), top-5 regenerate chips |
| `PromptEnhancementViewer.jsx` | Collapsible original vs enhanced prompt below assistant replies |
| `ModelControls.jsx` | Model toggles + Prompt Enhancement toggle |
| `AnalyticsDashboard.jsx` | Cost/savings KPIs, model table, history, **Export Report** CSV |
| `exportAnalyticsReport.js` | Client-side CSV builder (`tokenmaxx-analytics-report.csv`) |
| `AdminDashboard.jsx` | Employee usage |

---

## Tests

pytest suite in `backend/tests/` (30 tests):

| File | Coverage |
|------|----------|
| `test_auth.py` | Signup, login, JWT validation |
| `test_chat.py` | Chat + regenerate endpoints |
| `test_classifier.py` | LLM classifier + fallback |
| `test_routing.py` | Task-aware model selection per task type |
| `test_model_settings.py` | Model toggle sync + `explicitly_set` |
| `test_conversations.py` | Conversation detail + enhancement metadata |
| `test_health.py` | Health check |

Run: `cd backend && pytest -v`
