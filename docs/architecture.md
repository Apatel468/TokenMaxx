# SmartLLM Router — Architecture

> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.2.1 · **Last updated:** June 2026

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
| `prompt_analyzer` | prompt string | `AnalysisResult` | Keyword classify (current); LLM path planned |
| `prompt_enhancer` | prompt + task metadata + history | `EnhancementResult` | Groq AI agent JSON; rule fallback |
| `context_builder` | prompt + analysis + prior msgs | `PromptContext` | Calls enhancer; builds `message_history` |
| `router_engine` | `PromptContext` | `RoutingDecision` | Reads `models.yaml` |
| `config_loader` | — | YAML dict | Cached; task aliases |
| `model_clients` | model + context + messages | `ModelResponse` | Prepends system prompt; mock fallback |
| `response_cleaner` | raw model text | cleaned text | Strips `<think>` (Qwen) |
| `cost_tracker` | model + context + response | `CostEstimate` | vs GPT-4o baseline |
| `conversation_store` | turn data | `(conversation_id, title)` | SQLite CRUD; title on first reply |
| `conversation_title` | user msg + assistant reply | title string | Groq AI or rule fallback; 3–8 words |
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
  └─ keyword rules → task_type, confidence, keywords_matched
  (planned: Groq llama-3.1-8b-instant JSON classify + keyword fallback)
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
response_cleaner.clean_model_response()
        │
        ▼
cost_tracker.estimate_costs()
        │
        ▼
conversation_store.save_chat_turn()
  messages: original user text + assistant reply
  model_runs: routing, costs, enhanced_prompt, system_prompt, enhancement_reason
  title: generated once from first user + assistant exchange (if missing)
        │
        ▼
ChatResponse (title, enhancement_method, original + enhanced prompts)
```

---

## Prompt Classification (`prompt_analyzer.py`)

### Current: Keyword Classifier
- Regex word-boundary matching against `_KEYWORD_RULES`
- Returns: `task_type`, `confidence`, `keywords_matched`
- Extra analyzer types (summarization, creative_writing, etc.) mapped to YAML routes via `config_loader._TASK_ALIASES`

### Planned / Phase 3B: LLM Classifier
- **Model:** `groq/llama-3.1-8b-instant` (from `models.yaml` → `classifier`)
- **Output JSON:** `task_type`, `difficulty`, `risk_level`, `reason`
- **Allowed task_type:** keys in `models.yaml` → `models`
- Keyword fallback when Groq fails or no API key

> **Note:** `context_builder` currently passes `analysis.difficulty` and `analysis.risk_level` to the enhancer. The keyword-only analyzer must expose these fields (defaults) or the LLM classifier must be restored.

---

## Prompt Engineering (`prompt_enhancer.py`)

### Primary: AI Prompt Engineering Agent
- **Model:** `groq/llama-3.1-8b-instant` (`ENHANCER_MODEL` constant)
- **Output JSON:** `enhanced_prompt`, `system_prompt`, `enhancement_reason`
- **Inputs:** original prompt, `task_type`, `difficulty`, `risk_level`, conversation history
- **Rules:** Preserve user meaning; no fake facts; improve clarity/structure

### Fallback: Rule-Based Enhancement
- Fixed templates in `_TASK_RULES` (no API call)
- Sets `enhancement_method = "rule_fallback"`

### What gets sent to the response model
- **System message:** `system_prompt` from enhancer (+ Qwen-specific suffix in `model_clients`)
- **User history:** prior turns unchanged (original text from DB)
- **Latest turn:** `enhanced_prompt` (not raw user text)
- **Stored in DB:** user `messages.content` = original prompt; `model_runs.enhanced_prompt` = enhanced version

---

## Conversation Titles (`conversation_title.py` + `conversation_store.py`)

Titles are **not** derived from the user prompt alone.

| Rule | Behavior |
|------|----------|
| **When** | After the first assistant reply is saved |
| **Inputs** | First user message + first assistant response |
| **Length** | 3–8 words, ChatGPT-style noun phrase or concise question |
| **Primary** | Groq `llama-3.1-8b-instant` via LiteLLM JSON `{"title": "..."}` |
| **Fallback** | Rule-based patterns (F1, Python calculator, flashcards, keyword phrase) |
| **Persistence** | `conversations.title` — generated once, never overwritten |
| **API** | `POST /chat` returns `title`; list/detail endpoints backfill missing titles |
| **List backfill** | `GET /conversations` uses rule-based only (`use_ai=False`) to avoid rate limits |
| **Placeholder** | `"New Chat"` until first reply exists |

---

## Response Cleanup (`response_cleaner.py`)

Some Groq models (notably Qwen) emit `<think>...</think>` blocks. The cleaner:

1. Removes complete thinking blocks
2. Handles unclosed tags with heuristics (code fences, "Here's the answer", etc.)
3. Runs in `model_clients` before text is stored or returned

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

### `conversations`

| Column | Notes |
|--------|-------|
| `id`, `created_at`, `updated_at` | Thread metadata |
| `title` | Nullable; set after first assistant reply |

Migration: `database._migrate_conversations_columns()` adds `title` on startup.

### `messages`
- `role`: `"user"` or `"assistant"`
- User content = **original** prompt (not enhanced)

### `model_runs` (one row per AI reply)

| Column | Notes |
|--------|-------|
| Routing | task_type, selected_model, reason_selected |
| Tokens / cost | input_tokens, output_tokens, estimated_cost, premium_model_cost, savings_* |
| Performance | latency_ms, is_mock |
| Phase 4 | enhanced_prompt, system_prompt, enhancement_reason |

Migration: `database._migrate_model_runs_columns()` adds Phase 4 columns on startup.

### Legacy
- `chat_history` — unused

---

## Analytics Flow

- `GET /analytics/summary` — aggregates all `model_runs`
- `GET /analytics/history` — one row per `model_run` (newest first), includes `enhanced_prompt`
- `GET /analytics/model-usage` — grouped by `selected_model`

Frontend `AnalyticsDashboard.jsx` consumes these three endpoints only.

---

## Frontend Architecture

| File | Role |
|------|------|
| `App.jsx` | Chat \| Analytics tabs; 100vh shell |
| `ChatPage.jsx` | 3-column layout: sidebar \| thread \| routing panel |
| `AnalyticsDashboard.jsx` | KPI cards, model usage table, recent conversations |
| `utils/conversationTitle.js` | Resolves header/sidebar title; `"New Chat"` placeholder |
| `api/config.js` | `API_BASE = http://127.0.0.1:8001` |

**Layout:** Full viewport height, no page scroll; internal scroll in sidebar, message thread, and analytics panels.

**Not yet in UI:** `enhancement_method`, `enhanced_prompt`, `original_prompt` comparison panel.

---

## Service Dependency Graph

```
chat.py
  ├── prompt_analyzer
  ├── context_builder ──► prompt_enhancer
  ├── router_engine ──► config_loader
  ├── model_clients ──► response_cleaner
  │                  └── context_builder
  ├── cost_tracker
  └── conversation_store ──► conversation_title
```

---

## LiteLLM Integration Points

| Call site | Model | Purpose |
|-----------|-------|---------|
| `prompt_enhancer._enhance_with_ai` | `groq/llama-3.1-8b-instant` | Enhance prompt |
| `model_clients._call_groq` | `groq/{routed_model}` | Generate response |
| `conversation_title._generate_title_with_ai` | `groq/llama-3.1-8b-instant` | Title (first turn) |
| `prompt_analyzer` (planned) | `groq/llama-3.1-8b-instant` | Classify |

All use `GROQ_API_KEY`. Mock fallback on final response; rule fallbacks for enhance/title; keyword classify today.

---

## Future Scaling

| Concern | Current | Future |
|---------|---------|--------|
| Multiple Groq calls per turn | Sync blocking | Cache enhancement; async pipeline |
| Title backfill on list | Rule-based batch | Background job with rate limiting |
| Token limits | Full history | Truncation / summarization |
| DB | SQLite + ALTER migrations | PostgreSQL + Alembic |
| Auth | None | API keys / JWT |

---
