# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.4.0 · **Last updated:** June 2026

---

## System Architecture

| Tier | Role |
|------|------|
| **Presentation** | React SPA — Login, Chat (SSE streaming, routing panel, regenerate), Analytics (CSV export), Model Controls, Admin |
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
| `prompt_intelligence` | prompt + task + history | `PromptAnalysis` | v2: analyze → enhance by complexity + persona |
| `prompt_enhancer` | — | `PromptAnalysis` | Thin wrapper → `prompt_intelligence` |
| `context_builder` | prompt + flags | `PromptContext` | Holds `prompt_analysis`; skips when disabled |
| `groq_models` | — | `GroqModelRecord[]` | Allowlist-only catalog |
| `model_scorer` | task_type + candidates + prompt | `CandidateScore[]` | Complexity-aware weights + task bonuses |
| `router_engine` | context + DB + user | `RoutingDecision` | Best available model |
| `chat_service` | request + DB | prep, persist, `ChatResponse` | Shared by sync + stream |
| `model_clients` | model + context | `ModelResponse` / stream chunks | `generate_response` + `stream_response` |
| `regenerate_service` | turn + model_id | new assistant msg | Reuses stored prompts; non-streaming |
| `conversation_store` | turn data | ids, labels, prompt metadata | Router / regen labels |
| `report_generator` | DB | analytics rows | Per-user + admin |
| `sse` | event + data | SSE string | `format_sse()` helper |

---

## POST /chat/stream Data Flow (default frontend path)

```
Client → POST /chat/stream { prompt, conversation_id?, enhance_prompt? }
  → authenticate
  → prepare_chat_turn (classify → Prompt Intelligence v2 → route)
  → SSE: routing_start
  → SSE: routing_complete (task, model, top scores, prompt_analysis fields)
  → stream_response() → SSE: token (×N)
  → persist_chat_turn (after full text collected)
  → SSE: complete (full ChatResponse JSON)
```

## POST /chat Data Flow (sync — tests + API consumers)

```
Client → POST /chat { ... }
  → same prep as stream
  → generate_response() (blocking)
  → save → ChatResponse
```

## POST /chat/regenerate Data Flow

```
Client → POST /chat/regenerate { conversation_id, message_id, model_id }
  → load turn context from model_runs (no classify/enhance/route)
  → generate_response(selected model) — non-streaming
  → append assistant message ("User Selected Model")
```

---

## Prompt Intelligence v2

```
analyze_and_enhance(prompt, task_type, difficulty, ...)
  1. normalize_task_type (report → business, math → reasoning, …)
  2. compute_complexity_score (0–100) → simple | medium | complex
  3. select_persona, output_format, enhancement_strategy
  4. AI enhance (Groq JSON) OR rule-based v2 templates
  5. sanitize_enhanced_prompt — strip internal bracket scaffolding
```

Stored on `model_runs`: `prompt_complexity_score`, `prompt_complexity_level`, `prompt_persona`, `prompt_output_format`, `enhancement_strategy`, `prompt_enhancement_task_type`.

---

## Scoring Formula (routing)

```
complexity = f(prompt_length, task_type, complexity_keywords)
weights = dynamic(complexity)
composite = task_match×w_task + cost×w_cost + speed×w_speed
          + reasoning×w_reasoning + task_preference_bonus
```

---

## API Summary

| Area | Endpoints |
|------|-----------|
| Auth | `/auth/signup`, `/auth/login`, `/auth/me` |
| Chat | `POST /chat`, `POST /chat/stream`, `POST /chat/regenerate` |
| Preferences | `GET/PUT /user/preferences` |
| Model Controls | `GET/PUT /model-settings` |
| Analytics | `/analytics/summary`, `/history`, `/model-usage` |
| Admin | `GET /admin/employee-usage` |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `model_runs` | Costs, tokens, enhancement, classification, **prompt intelligence v2** metadata |
| `messages` | Content + `response_label` |
| `conversations` | Threads + title + `user_id` |
| `users` | Accounts + role |
| `user_preferences` | `enhance_prompts` |
| `admin_model_settings` / `user_model_settings` | Model toggles |

---

## Frontend

| Component | Responsibility |
|-----------|----------------|
| `ChatPage.jsx` | SSE streaming UI, typing cursor, Latest Routing panel, regenerate chips |
| `chat.js` | `streamChat()` — fetch + ReadableStream SSE parser |
| `PromptEnhancementViewer.jsx` | Collapsible v2 metadata: task, complexity, persona, strategy, prompts |
| `AnalyticsDashboard.jsx` | KPIs + **Export Report** CSV |
| `ModelControls.jsx` | Model toggles + enhancement toggle |
| `AdminDashboard.jsx` | Employee usage |

---

## Tests (39)

| File | Coverage |
|------|----------|
| `test_auth.py` | Signup, login, JWT |
| `test_chat.py` | Sync chat + regenerate |
| `test_chat_stream.py` | SSE events (routing_start, token, complete) |
| `test_classifier.py` | LLM classifier + fallback |
| `test_prompt_intelligence.py` | v2 enhancement by task/complexity |
| `test_routing.py` | Task-aware model selection |
| `test_model_settings.py` | Toggle sync |
| `test_conversations.py` | Thread detail + `prompt_analysis` |
| `test_health.py` | Health check |

Run: `cd backend && pytest -v`
