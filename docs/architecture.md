# SmartLLM Router — Architecture

> Technical architecture reference. Pair with `project_memory.md` for context.

---

## System Architecture

SmartLLM Router is a **monolithic two-tier application**:

| Tier | Role |
|------|------|
| **Presentation** | React SPA (Vite dev server or static build) |
| **Application** | FastAPI monolith with service layer |
| **Data** | SQLite file database |
| **External** | Groq API via LiteLLM |

There is no separate BFF, message queue, cache, or auth service in the MVP.

```
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
                           │ HTTP
              ┌────────────▼────────────┐
              │   React Frontend        │
              │   (port 5173)           │
              └────────────┬────────────┘
                           │ JSON REST
              ┌────────────▼────────────┐
              │   FastAPI Backend       │
              │   (port 8001)           │
              │                         │
              │  ┌─────────────────┐   │
              │  │    Routers      │   │
              │  └────────┬────────┘   │
              │           │             │
              │  ┌────────▼────────┐   │
              │  │    Services     │   │
              │  └────────┬────────┘   │
              │           │             │
              │  ┌────────▼────────┐   │
              │  │ SQLAlchemy ORM  │   │
              │  └────────┬────────┘   │
              └───────────┼─────────────┘
                          │
              ┌───────────▼───────────┐
              │  smartllm_router.db   │
              └───────────────────────┘
                          │
              ┌───────────▼───────────┐
              │  Groq API (LiteLLM)   │
              └───────────────────────┘
```

---

## Backend Architecture

### Layering

```
main.py
  └── routers/          HTTP layer — thin, delegates to services
        └── services/   Business logic — no HTTP concerns
              └── database.py   Persistence models
              └── config/models.yaml   Externalized routing config
```

**Principle:** Routers validate I/O (Pydantic) and orchestrate; services contain logic.

### Router Modules

| Module | Prefix | Responsibility |
|--------|--------|------------------|
| `chat.py` | `/chat` | End-to-end chat pipeline |
| `conversations.py` | `/conversations` | List/load threads |
| `analytics.py` | `/analytics` | Aggregated stats |
| `models.py` | `/models` | Model catalog from YAML |

### Service Modules

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| `prompt_analyzer` | prompt string | `AnalysisResult` | Keyword regex matching |
| `context_builder` | prompt + analysis + prior messages | `PromptContext` | Token estimates, message_history |
| `router_engine` | `PromptContext` | `RoutingDecision` | Reads YAML via config_loader |
| `config_loader` | — | YAML dict | Cached; task aliases |
| `model_clients` | groq_model + context + messages | `ModelResponse` | LiteLLM or mock |
| `cost_tracker` | model_id + context + response | `CostEstimate` | YAML pricing |
| `conversation_store` | chat turn data | conversation_id | CRUD for threads |
| `report_generator` | DB session | analytics DTOs | Aggregations |

### Application Lifecycle

1. `load_dotenv()` in `main.py` before imports that need env
2. `logging.basicConfig` at INFO level
3. `lifespan` → `init_db()` creates tables via SQLAlchemy `create_all`
4. CORS middleware for Vite origins only

---

## Frontend Architecture

### Structure

```
App.jsx                    Tab shell (Chat | Analytics)
├── ChatPage.jsx           3-column: sidebar | thread | routing panel
└── AnalyticsDashboard.jsx Summary + tables + history

api/
├── config.js              API_BASE constant
├── chat.js                POST /chat
├── conversations.js       GET /conversations*
└── analytics.js           GET /analytics/*
```

**No React Router** — tab state is local `useState` in `App.jsx`.

**No global state library** — each component manages its own fetch/state.

### ChatPage State Model

| State | Purpose |
|-------|---------|
| `conversationId` | Active thread (null = new chat) |
| `messages` | Current thread messages for display |
| `conversations` | Sidebar list from GET /conversations |
| `prompt` | Input textarea value |
| `result` | Latest POST /chat routing response |
| `loading` / `error` | UX flags |

### Data Flow (Frontend)

```
User submits prompt
  → sendChat(prompt, conversationId)
  → POST /chat
  → response includes conversation_id
  → fetchConversation(id) to refresh thread
  → loadConversationList() to refresh sidebar
  → onChatComplete() bumps analytics refresh counter
```

---

## Data Flow — POST /chat (Detailed)

```
Client JSON: { prompt, conversation_id? }
        │
        ▼
┌───────────────────┐
│ conversation_store│──► load_message_history (if id set)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ prompt_analyzer   │──► task_type, confidence, keywords
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ context_builder   │──► estimated tokens, message_history[]
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ router_engine     │──► groq model + reason (from YAML)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ model_clients     │──► LiteLLM completion(full history)
└───────────────────┘    or mock if no key / error
        │
        ▼
┌───────────────────┐
│ cost_tracker      │──► actual vs premium costs
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ conversation_store│──► save user msg, assistant msg, model_run
└───────────────────┘
        │
        ▼
ChatResponse JSON to client
```

---

## API Flow — Read Endpoints

### Conversations
- `GET /conversations` → `conversation_store.list_conversations`
- `GET /conversations/{id}` → `conversation_store.get_conversation_detail`

### Analytics
- `GET /analytics/summary` → `report_generator.generate_analytics_summary` (aggregates `model_runs`)
- `GET /analytics/history` → `report_generator.get_history` (maps conversation records)
- `GET /analytics/model-usage` → `report_generator.get_model_usage` (groups `model_runs` by model)

### Models
- `GET /models` → reads `models.yaml` pricing + routing entries

---

## Model Routing Flow

```
User prompt (latest message only for classification)
        │
        ▼
┌─────────────────────────────────────┐
│ prompt_analyzer._KEYWORD_RULES      │
│ Score keyword hits per task type    │
│ Winner = highest score, else QA     │
└─────────────────┬───────────────────┘
                  │ task_type
                  ▼
┌─────────────────────────────────────┐
│ config_loader.get_route_for_task    │
│ 1. Direct YAML match                │
│ 2. Alias (e.g. summarization→report)│
│ 3. default_task: general_qa         │
└─────────────────┬───────────────────┘
                  │
                  ▼
         models.yaml entry:
         { provider: groq, model: ..., reason: ... }
                  │
                  ▼
┌─────────────────────────────────────┐
│ model_clients._to_litellm_model     │
│ → groq/{model_name}               │
│ litellm.completion(messages=history)│
└─────────────────────────────────────┘
```

### Current YAML Routing Table

| YAML Key | Groq Model | Use Case |
|----------|------------|----------|
| `flashcards` | `llama-3.3-70b-versatile` | Educational / flashcard tasks |
| `coding` | `qwen/qwen3-32b` | Code and reasoning |
| `general_qa` | `llama-3.1-8b-instant` | Fast cheap Q&A |
| `report` | `llama-3.3-70b-versatile` | Reports, writing (also alias target) |

### Task Type Aliases (analyzer → YAML)

| Analyzer Output | Routed Via |
|-----------------|------------|
| `summarization` | `report` |
| `creative_writing` | `report` |
| `data_analysis` | `report` |
| `translation` | `general_qa` |
| unmatched | `default_task` → `general_qa` |

---

## Database Schema

### Entity Relationship

```
conversations (1) ──< (N) messages
conversations (1) ──< (N) model_runs
messages (1) ──< (0..1) model_runs.assistant_message_id
```

### Table: `conversations`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Exposed as `conversation_id` |
| created_at | DATETIME UTC | |
| updated_at | DATETIME UTC | Updated on new messages |

### Table: `messages`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| conversation_id | FK | Indexed |
| role | STRING(20) | `user` or `assistant` |
| content | TEXT | Full prompt/response |
| created_at | DATETIME UTC | |

### Table: `model_runs`

One row per assistant reply (per `/chat` turn).

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| conversation_id | FK | |
| assistant_message_id | FK nullable | Links to assistant message |
| task_type | STRING | From analyzer |
| selected_model | STRING | Groq model id from YAML |
| reason_selected | TEXT | From YAML |
| input_tokens, output_tokens | INTEGER | From LiteLLM or estimate |
| estimated_cost | FLOAT | USD |
| premium_model_cost | FLOAT | USD (GPT-4o baseline) |
| savings_usd | FLOAT | premium - actual |
| savings_percentage | FLOAT | |
| latency_ms | FLOAT | Wall clock |
| is_mock | BOOLEAN | True if mock response |
| created_at | DATETIME UTC | |

### Legacy: `chat_history`

Flat table from Phase 1. **Not written by current code.** Safe to deprecate.

---

## Service Relationships (Dependency Graph)

```
chat.py
  ├── prompt_analyzer
  ├── context_builder ──► prompt_analyzer (types only)
  ├── router_engine ──► config_loader, context_builder
  ├── model_clients ──► context_builder
  ├── cost_tracker ──► config_loader, context_builder, model_clients
  └── conversation_store ──► cost_tracker, model_clients, router_engine

analytics.py ──► report_generator ──► database models

conversations.py ──► conversation_store

models.py ──► config_loader
```

**Note:** `cost_tracker` imports `ModelResponse` from `model_clients` — avoid circular imports if refactoring.

---

## Future Scaling Considerations

| Concern | Current | Future Approach |
|---------|---------|-----------------|
| Database | SQLite file | PostgreSQL for concurrency |
| Config hot-reload | In-memory cache | File watcher or admin API |
| LLM calls | Sync blocking | Async + streaming + queue |
| Auth | None | API keys per user, JWT |
| Horizontal scale | Single process | Stateless API + shared DB |
| Token limits | Full history sent | Summarization / sliding window |
| Observability | stdout logs | Structured logging, metrics |
| Provider failover | Mock fallback | Multi-provider retry chain |
| Frontend | Hardcoded API URL | Env-based config, CDN deploy |

---

## Deployment Topology (Future)

```
[CDN] → Static React build
          ↓
[Load Balancer] → [FastAPI x N] → [PostgreSQL]
                        ↓
                   [LiteLLM Proxy] → Groq / others
```

Not implemented in MVP.
