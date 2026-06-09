# SmartLLM Router — Architectural Decisions

> Record of major decisions, tradeoffs, and rules for future developers.  
> **Version:** 0.2.2 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Backend | FastAPI | OpenAPI, Pydantic, async-ready |
| Database | SQLite | Zero setup for MVP |
| LLM gateway | LiteLLM | Unified Groq interface |
| Provider | Groq only | Cost/speed for demo |
| Frontend | React + Vite | Fast iteration |
| Routing config | YAML | Change models without code deploy |
| Styling | Plain CSS | No UI framework dependency |

---

## Architectural Decisions

### Service layer 🔒
Routers orchestrate; business logic lives in `backend/services/`.

### YAML-driven Groq routing 🔒
**Decision:** `router_engine.py` reads `models.yaml` via `config_loader` — no hard-coded OpenAI model names.  
**Output:** `RoutingDecision` includes `groq_model` for LiteLLM and `model_id` for cost lookup.  
**Why:** Single config file controls routing, pricing, and classifier allowed types.

### Keyword classifier with optional LLM upgrade
**Decision:** Keyword rules classify `task_type` today; `difficulty` and `risk_level` default to `"medium"` / `"low"`.  
**Planned:** Groq LLM classifier as primary with keyword fallback.  
**Why:** Pipeline works without extra Groq call; LLM classify improves accuracy when restored.

### AI prompt engineering with rule fallback
**Decision:** Groq `llama-3.1-8b-instant` returns JSON enhancement; rules on failure.  
**Tradeoff:** One Groq call per turn for enhancement.

### Original prompt preserved in DB 🔒
User `messages.content` = original text; `model_runs.enhanced_prompt` = what was sent to the model.

### Conversation titles after first reply
**Decision:** Title from first user message **and** first assistant response.  
**Rules:** 3–8 words; store once in `conversations.title`; list backfill uses rules only (no AI batch).

### Response cleanup
Strip `<think>` from Qwen output before storage/display.

### Cost baseline 🔒
GPT-4o rates from `models.yaml` → `premium_baseline` — illustrative, not a live API call.

### CORS for dev ports
Allow `localhost` / `127.0.0.1` on **5173** and **5174** because Vite may shift ports when 5173 is busy.

### Schema migration via startup ALTER
`database._migrate_*_columns()` on app start — replace with Alembic before production 🔒.

---

## Groq Touchpoints (with API key)

| Step | File | When | Model |
|------|------|------|-------|
| Enhance | `prompt_enhancer.py` | Every turn | 8B instant |
| Respond | `model_clients.py` | Every turn | YAML routed |
| Title | `conversation_title.py` | First turn | 8B instant |
| Classify | `prompt_analyzer.py` | (planned) | 8B instant |

---

## Prompt Comparison (original vs enhanced)

Not a standalone module.

| Location | What |
|----------|------|
| `prompt_enhancer.py` | Produces `enhanced_prompt` |
| `POST /chat` | Returns `original_prompt` + `enhanced_prompt` |
| `model_runs` | Stores `enhanced_prompt` for analytics |
| Frontend | Not displayed yet (M11 todo) |

---

## Things NOT to Change Without Review 🔒

| Item | Reason |
|------|--------|
| `models.yaml` structure | Breaks routing, pricing, classifier |
| `RoutingDecision.groq_model` field | Breaks `chat.py` → `model_clients` |
| `model_runs` enhancement columns | Breaks analytics |
| Original prompt in `messages` | UI/audit correctness |
| Title generated-once rule | Sidebar consistency |
| Groq-only in `model_clients` | Scope control |

---

## Rejected Alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Hard-coded OpenAI routing table | Replaced by Groq + YAML in Phase 2 |
| Title from user prompt only | Keyword soup titles |
| AI title backfill on every list load | Groq rate limits |
| Enhancing full conversation history each turn | Cost + complexity |

---

## Decision Log

| Date / Phase | Decision |
|--------------|----------|
| Phase 2 | Groq-only, YAML routing, `RoutingDecision.groq_model` |
| Phase 3B | LLM classifier design (keyword fallback) |
| Phase 4 | AI prompt engineering agent |
| M11 | Titles from first exchange; response cleanup; 100vh UI |
| v0.2.2 | Restored YAML router + cost_tracker; analyzer defaults; CORS 5174 |

---

## Open Questions

1. Restore LLM classifier in `prompt_analyzer.py`?
2. Move enhancer/title model names to `models.yaml`?
3. Store `enhancement_method` in SQLite?
4. Rename `mock_response` → `response`?
5. Add README.md at repo root for onboarding?

---
