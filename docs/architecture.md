# TokenMaxx — Architecture

> **Tagline:** Maximum Intelligence, Minimum Cost  
> Technical architecture reference. Pair with `project_memory.md` for context.  
> **Version:** 0.3.0 · **Last updated:** June 2026

---

## System Architecture

| Tier | Role |
|------|------|
| **Presentation** | React SPA (Vite, port 5173 or 5174) — Chat, Analytics, Model Controls |
| **Application** | FastAPI monolith (port 8001) |
| **Data** | SQLite (`smartllm_router.db`) |
| **External** | Groq API via LiteLLM + `GET /openai/v1/models` for catalog sync |

---

## Backend Service Layer

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| `prompt_analyzer` | prompt | `AnalysisResult` | Keyword classify |
| `prompt_enhancer` | prompt + metadata | `EnhancementResult` | Groq AI JSON; rule fallback |
| `context_builder` | prompt + analysis + history | `PromptContext` | Builds `message_history` |
| `groq_models` | — | `GroqModelRecord[]` | API + registry merge; logs missing models |
| `model_scorer` | task_type + candidates | `CandidateScore[]` | Composite routing formula |
| `router_engine` | `PromptContext` + DB | `RoutingDecision` | Picks best enabled model |
| `model_settings` | DB | enable/disable state | Seeds from routable catalog |
| `config_loader` | — | YAML dict | Task profiles, auxiliary models |
| `model_clients` | model + context | `ModelResponse` | LiteLLM; mock fallback |
| `cost_tracker` | model + response | `CostEstimate` | Registry pricing vs GPT-4o |
| `conversation_store` | turn data | `(id, title)` | Persists messages + model_runs |

---

## POST /chat Data Flow

```
Client → POST /chat { prompt, conversation_id? }
  → load_message_history()
  → analyze_prompt()           # keyword → task_type
  → build_context()            # enhance_prompt()
  → route(context, db)         # score all enabled Groq models
  → generate_response()        # LiteLLM
  → clean_model_response()
  → estimate_costs()
  → save_chat_turn()
  → ChatResponse (+ routing_score, candidate_models)
```

---

## Dynamic Model Routing

### Configuration split

| File | Purpose |
|------|---------|
| `config/model_registry.py` | Per-model metadata: scores, cost, latency, strengths |
| `config/models.yaml` | Task profiles (capability weights), auxiliary models, premium baseline |
| SQLite `model_settings` | User enable/disable per model id |

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

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/settings/models` | List routable models + enabled state |
| PUT | `/settings/models` | Bulk enable/disable toggles |

---

## Cost Tracking (`cost_tracker.py`)

- Rates from `model_registry.py` via `cost_per_1k_tokens()`
- Baseline from `models.yaml` → `premium_baseline`

---

## Frontend Tabs

| Tab | Component | Notes |
|-----|-----------|-------|
| Chat | `ChatPage.jsx` | 3-column; routing score + top candidates |
| Analytics | `AnalyticsDashboard.jsx` | KPIs, model table, history — vertical scroll only |
| Model Controls | `ModelControls.jsx` | Toggle routable Groq models |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `conversations` | Thread metadata + title |
| `messages` | User/assistant content |
| `model_runs` | Routing, tokens, costs per reply |
| `model_settings` | `model_id` + `enabled` flag |
