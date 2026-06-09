# SmartLLM Router — Architecture

> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.2.2 · **Last updated:** June 2026

---

## System Architecture

| Tier | Role |
|------|------|
| **Presentation** | React SPA (Vite, port 5173 or 5174) |
| **Application** | FastAPI monolith (port 8001) |
| **Data** | SQLite (`smartllm_router.db`) |
| **External** | Groq API via LiteLLM |

CORS in `main.py` allows `localhost` and `127.0.0.1` on ports **5173** and **5174** (Vite picks 5174 when 5173 is in use).

---

## Backend Service Layer

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| `prompt_analyzer` | prompt | `AnalysisResult` | Keyword classify; default `difficulty`/`risk_level` |
| `prompt_enhancer` | prompt + metadata + history | `EnhancementResult` | Groq AI JSON; rule fallback |
| `context_builder` | prompt + analysis + history | `PromptContext` | Builds `message_history` |
| `router_engine` | `PromptContext` | `RoutingDecision` | `groq_model` from `models.yaml` |
| `config_loader` | — | YAML dict | Routes, pricing, aliases |
| `model_clients` | model + context + messages | `ModelResponse` | LiteLLM; mock fallback |
| `response_cleaner` | raw text | cleaned text | Strips Qwen thinking tags |
| `cost_tracker` | model + context + response | `CostEstimate` | YAML pricing vs GPT-4o baseline |
| `conversation_store` | turn data | `(id, title)` | Persists messages + model_runs |
| `conversation_title` | user + assistant text | title string | 3–8 words; once per thread |
| `report_generator` | DB session | analytics DTOs | |

---

## POST /chat Data Flow

```
Client → POST /chat { prompt, conversation_id? }
  → load_message_history()
  → analyze_prompt()           # keyword → task_type
  → build_context()            # enhance_prompt() → enhanced_prompt, system_prompt
  → route()                    # models.yaml → groq_model
  → generate_response()        # LiteLLM
  → clean_model_response()
  → estimate_costs() + log_request_metrics()
  → save_chat_turn()           # + title on first reply
  → ChatResponse
```

---

## Prompt Classification (`prompt_analyzer.py`)

**Current implementation:**
- Word-boundary keyword scoring against `_KEYWORD_RULES`
- Output: `task_type`, `confidence`, `keywords_matched`
- Defaults: `difficulty="medium"`, `risk_level="low"` (used by `prompt_enhancer`)

**Task alias mapping** (`config_loader._TASK_ALIASES`):
- summarization, creative_writing, data_analysis → `report`
- translation → `general_qa`

**Planned (Phase 3B):** Groq `llama-3.1-8b-instant` JSON classifier with keyword fallback.

---

## Model Routing (`router_engine.py`)

Reads `config_loader.get_route_for_task(task_type)` — **no hard-coded model table**.

```python
@dataclass
class RoutingDecision:
    model_id: str       # Groq model id (cost lookup)
    model_label: str    # "Groq / {model}"
    reason: str
    groq_model: str     # Passed to model_clients / LiteLLM
    provider: str       # "groq"
```

| YAML Key | Groq Model |
|----------|------------|
| `flashcards` | `llama-3.3-70b-versatile` |
| `coding` | `qwen/qwen3-32b` |
| `general_qa` | `llama-3.1-8b-instant` |
| `report` | `llama-3.3-70b-versatile` |

---

## Cost Tracking (`cost_tracker.py`)

- Rates from `models.yaml` → `pricing` (per Groq model)
- Baseline from `premium_baseline` (GPT-4o illustrative rates)
- Uses real `input_tokens` from LiteLLM when available
- `log_request_metrics()` writes structured INFO log per request

---

## Prompt Engineering (`prompt_enhancer.py`)

- **AI:** Groq `llama-3.1-8b-instant` → JSON `enhanced_prompt`, `system_prompt`, `enhancement_reason`
- **Fallback:** `_TASK_RULES` templates → `enhancement_method = "rule_fallback"`
- Only the **latest** user turn is enhanced; prior DB messages stay original

**Prompt comparison** (original vs enhanced):
- `POST /chat` → `original_prompt` + `enhanced_prompt`
- `model_runs.enhanced_prompt` in analytics history
- No separate comparison service

---

## Conversation Titles

| Rule | Detail |
|------|--------|
| Trigger | After first assistant reply saved |
| Inputs | First user message + first assistant response |
| AI model | `llama-3.1-8b-instant` |
| Length | 3–8 words, ChatGPT-style |
| Storage | `conversations.title` — never overwritten |
| List API | Rule-based backfill only (`use_ai=False`) |
| Placeholder | `"New Chat"` until title exists |

---

## Database Schema

- **`conversations`** — `id`, timestamps, `title` (nullable)
- **`messages`** — `role`, `content` (user = original prompt)
- **`model_runs`** — routing, tokens, costs, `enhanced_prompt`, `system_prompt`, `enhancement_reason`
- **`chat_history`** — legacy, unused

Migrations on startup: `_migrate_model_runs_columns()`, `_migrate_conversations_columns()`.

---

## Frontend

| File | Role |
|------|------|
| `App.jsx` | Chat \| Analytics tabs |
| `ChatPage.jsx` | Sidebar + thread + routing panel |
| `AnalyticsDashboard.jsx` | Summary, model usage, history |
| `api/config.js` | `API_BASE = http://127.0.0.1:8001` |
| `utils/conversationTitle.js` | Title display helpers |

---

## LiteLLM Call Sites

| File | Model | When |
|------|-------|------|
| `prompt_enhancer` | `groq/llama-3.1-8b-instant` | Every turn |
| `model_clients` | `groq/{routed}` | Every turn |
| `conversation_title` | `groq/llama-3.1-8b-instant` | First turn only |
| `prompt_analyzer` | (planned) | — |

---

## Service Dependency Graph

```
chat.py
  ├── prompt_analyzer
  ├── context_builder → prompt_enhancer
  ├── router_engine → config_loader
  ├── model_clients → response_cleaner
  ├── cost_tracker → config_loader
  └── conversation_store → conversation_title
```

---
