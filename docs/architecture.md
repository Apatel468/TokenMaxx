# SmartLLM Router — Architecture

> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.2.0 · **Last updated:** June 2026

---

## System Architecture

SmartLLM Router is a **monolithic two-tier application**:

| Tier | Role |
|------|------|
| **Presentation** | React SPA (Vite, port 5173) |
| **Application** | FastAPI monolith (port 8001) |
| **Data** | SQLite (`smartllm_router.db`) |
| **External** | Groq API via LiteLLM |

No background workers, agents framework, or auth service in MVP.

---

## Backend Service Layer

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| `prompt_analyzer` | prompt string | `AnalysisResult` | Groq LLM JSON classify; keyword fallback |
| `prompt_enhancer` | prompt + task metadata + history | `EnhancementResult` | Groq AI agent JSON; rule fallback |
| `context_builder` | prompt + analysis + prior msgs | `PromptContext` | Calls enhancer; builds `message_history` |
| `router_engine` | `PromptContext` | `RoutingDecision` | Reads `models.yaml` |
| `config_loader` | — | YAML dict | Cached; task aliases |
| `model_clients` | model + context + messages | `ModelResponse` | Prepends system prompt; mock fallback |
| `cost_tracker` | model + context + response | `CostEstimate` | vs GPT-4o baseline |
| `conversation_store` | turn data | `conversation_id` | SQLite CRUD |
| `report_generator` | DB session | analytics DTOs | Per-`model_run` history |

---

## POST /chat Data Flow

```
Client: { prompt, conversation_id? }
        │
        ▼
conversation_store.load_message_history()
        │
        ▼
prompt_analyzer.analyze_prompt()
  ├─ Groq llama-3.1-8b-instant (JSON: task_type, difficulty, risk_level, reason)
  └─ fallback: keyword rules
        │
        ▼
context_builder.build_context()
  └─ prompt_enhancer.enhance_prompt()
       ├─ Groq llama-3.1-8b-instant (JSON: enhanced_prompt, system_prompt, reason)
       └─ fallback: rule-based templates
        │
        ▼
router_engine.route() → models.yaml
        │
        ▼
model_clients.generate_response()
  messages = [system_prompt] + prior_history + [enhanced_user_message]
  └─ Groq routed model OR mock
        │
        ▼
cost_tracker.estimate_costs()
        │
        ▼
conversation_store.save_chat_turn()
  messages: original user text + assistant reply
  model_runs: routing, costs, enhanced_prompt, system_prompt, enhancement_reason
        │
        ▼
ChatResponse (includes enhancement_method: "ai" | "rule_fallback")
```

---

## Prompt Classification (`prompt_analyzer.py`)

### Primary: LLM Classifier
- **Model:** `groq/llama-3.1-8b-instant` (from `models.yaml` → `classifier`)
- **Output JSON:** `task_type`, `difficulty`, `risk_level`, `reason`
- **Allowed task_type:** keys in `models.yaml` → `models` (flashcards, coding, general_qa, report)

### Fallback: Keyword Classifier
- Regex word-boundary matching
- Extra types: summarization, creative_writing, data_analysis, translation
- Mapped to YAML via `config_loader._TASK_ALIASES`

---

## Prompt Engineering (`prompt_enhancer.py`)

### Primary: AI Prompt Engineering Agent
- **Model:** `groq/llama-3.1-8b-instant` (`ENHANCER_MODEL` constant)
- **Output JSON:** `enhanced_prompt`, `system_prompt`, `enhancement_reason`
- **Rules:** Preserve user meaning; no fake facts; improve clarity/structure
- **Task hints:** flashcards (Q/A), coding (comments/edge cases), report (headings), summarization (bullets), general_qa (concise)

### Fallback: Rule-Based Enhancement
- Fixed templates in `_TASK_RULES` (no API call)
- Same safety constraints appended to system prompt
- Sets `enhancement_method = "rule_fallback"`

### What gets sent to the response model
- **System message:** `system_prompt` from enhancer
- **User history:** prior turns unchanged (original text from DB)
- **Latest turn:** `enhanced_prompt` (not raw user text)
- **Stored in DB:** user `messages.content` = original prompt; `model_runs.enhanced_prompt` = enhanced version

---

## Model Routing (`router_engine.py` + `models.yaml`)

| YAML Key | Groq Model | Use Case |
|----------|------------|----------|
| `flashcards` | `llama-3.3-70b-versatile` | Educational Q/A |
| `coding` | `qwen/qwen3-32b` | Code / reasoning |
| `general_qa` | `llama-3.1-8b-instant` | Fast cheap Q&A |
| `report` | `llama-3.3-70b-versatile` | Reports / writing |

**Aliases:** summarization/creative_writing/data_analysis → report; translation → general_qa

---

## Database Schema

### `model_runs` (one row per AI reply)

| Column | Notes |
|--------|-------|
| Routing | task_type, selected_model, reason_selected |
| Tokens / cost | input_tokens, output_tokens, estimated_cost, premium_model_cost, savings_* |
| Performance | latency_ms, is_mock |
| **Phase 4** | enhanced_prompt, system_prompt, enhancement_reason |

Migration: `database._migrate_model_runs_columns()` adds columns to existing DBs on startup.

### Other tables
- `conversations` — thread metadata
- `messages` — user/assistant content (user = **original** prompt)
- `chat_history` — legacy, unused

---

## Analytics Flow

- `GET /analytics/summary` — aggregates all `model_runs`
- `GET /analytics/history` — one row per `model_run` (newest first), includes `enhanced_prompt`
- `GET /analytics/model-usage` — grouped by `selected_model`

---

## Frontend Architecture

- `App.jsx` — Chat | Analytics tabs
- `ChatPage.jsx` — sidebar, thread, routing panel (does not yet show enhancement fields)
- `AnalyticsDashboard.jsx` — summary, model usage, history
- `api/config.js` — `API_BASE = http://127.0.0.1:8001`

---

## Service Dependency Graph

```
chat.py
  ├── prompt_analyzer
  ├── context_builder ──► prompt_enhancer
  │                    └── prompt_analyzer (types)
  ├── router_engine ──► config_loader
  ├── model_clients ──► context_builder
  ├── cost_tracker
  └── conversation_store
```

---

## LiteLLM Integration Points

| Call site | Model | Purpose |
|-----------|-------|---------|
| `prompt_analyzer._analyze_with_llm` | `groq/llama-3.1-8b-instant` | Classify |
| `prompt_enhancer._enhance_with_ai` | `groq/llama-3.1-8b-instant` | Enhance |
| `model_clients._call_groq` | `groq/{routed_model}` | Generate response |

All use `GROQ_API_KEY` from environment. Mock fallback only on final response step (and rule fallbacks for classify/enhance).

---

## Future Scaling

| Concern | Current | Future |
|---------|---------|--------|
| 3 Groq calls per turn | Sync blocking | Cache classification; async pipeline |
| Token limits | Full history | Truncation / summarization |
| DB | SQLite + ALTER migrations | PostgreSQL + Alembic |
| Auth | None | API keys / JWT |

---
