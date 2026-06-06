# SmartLLM Router — Architectural Decisions

> Record of major decisions, tradeoffs, and rules for future developers.  
> **Version:** 0.2.0 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

(Unchanged from v0.1 — FastAPI, SQLite, LiteLLM, Groq-only, React+Vite, YAML config, plain CSS.)

See prior sections in git history or `project_memory.md` for full rationale.

---

## Architectural Decisions

### Service layer between routers and persistence 🔒
Business logic in `backend/services/`; routers orchestrate only.

### LLM classifier with keyword fallback (Phase 3B)
**Decision:** Primary classification via Groq `llama-3.1-8b-instant` + LiteLLM JSON mode; keyword rules as fallback.  
**Why:** More accurate task routing than keywords alone; still works offline without API key.  
**Tradeoff:** Extra Groq call (+latency, +cost) on every chat request.  
**Config:** `models.yaml` → `classifier` block; allowed types from `models` keys.

### AI Prompt Engineering Agent with rule fallback (Phase 4)
**Decision:** Primary enhancement via Groq `llama-3.1-8b-instant` returning JSON (`enhanced_prompt`, `system_prompt`, `enhancement_reason`); rule templates as fallback.  
**Why:** Smarter prompt wrapping than static templates; preserves user intent with explicit safety rules in agent prompt.  
**Tradeoff:** Second Groq call per request; total of **3 Groq calls** when API key present (classify + enhance + respond).  
**Model location:** Hardcoded `ENHANCER_MODEL` in `prompt_enhancer.py` (same as classifier — cheapest Groq model).  
**API:** `enhancement_method` field exposes `"ai"` vs `"rule_fallback"`.

### Original user text preserved in DB
**Decision:** `messages.content` for user role stores **original** prompt; enhanced version stored on `model_runs.enhanced_prompt`.  
**Why:** UI shows what user typed; analytics can audit what was sent to the model.

### System prompt sent separately to LiteLLM
**Decision:** `model_clients._build_litellm_messages()` prepends `{"role": "system", "content": system_prompt}` before history.  
**Why:** Standard chat API pattern; downstream model gets clear behavioral instructions.

### Only latest user turn is enhanced in multi-turn chats
**Decision:** Prior messages in `message_history` stay as originally stored; only the new message gets AI/rule enhancement.  
**Why:** Avoid re-processing entire thread each turn; prior assistant replies already reflect earlier context.

### GPT-4o as savings baseline 🔒
Illustrative savings vs premium — not a live OpenAI call.

### Mock fallback on final response only (enhance/classify use rules)
**Decision:** Missing key → keyword classify + rule enhance + mock chat response.  
**Why:** Demo still works end-to-end without Groq.

### Analytics per `model_run` (fixed in Phase 4)
**Decision:** `GET /analytics/history` iterates `model_runs`, not one row per conversation.  
**Why:** Multi-turn threads produce multiple turns; each includes `enhanced_prompt`.

### Schema migration via startup ALTER
**Decision:** `database._migrate_model_runs_columns()` adds Phase 4 columns to existing SQLite DBs.  
**Why:** No Alembic yet; `create_all` doesn't alter existing tables.  
**Tradeoff:** Fragile for production — migrate to Alembic before deploy 🔒.

---

## Assumptions

1. Single user / no auth
2. English prompts (classifier + enhancer tuned for English)
3. One shared `GROQ_API_KEY`
4. ~4 chars/token when usage missing
5. Three Groq calls per chat acceptable for MVP demo cost

---

## Important Implementation Notes

### Environment variables
- `GROQ_API_KEY` — used by `prompt_analyzer`, `prompt_enhancer`, `model_clients`
- **🔒 NEVER read, log, or commit `.env` contents**

### LiteLLM model strings
```
llama-3.1-8b-instant  →  groq/llama-3.1-8b-instant
qwen/qwen3-32b        →  groq/qwen/qwen3-32b
```

### Three Groq touchpoints per request (with API key)
| Step | File | Model |
|------|------|-------|
| Classify | `prompt_analyzer.py` | classifier from YAML (8B instant) |
| Enhance | `prompt_enhancer.py` | ENHANCER_MODEL (8B instant) |
| Respond | `model_clients.py` | routed from YAML |

### Config cache
Restart uvicorn after editing `models.yaml`.

### Response field naming debt
- `ChatResponse.mock_response` — holds real Groq text too (legacy name)
- Plan rename in M12

---

## Things NOT to Change Without Review 🔒

| Item | Reason |
|------|--------|
| `config/models.yaml` structure | Breaks config_loader, classifier allowed types |
| `model_runs` schema + enhancement columns | Breaks analytics |
| Mock fallback on chat response | Demo reliability |
| GPT-4o baseline semantics | Product story |
| Preserve-original-prompt-in-messages rule | UI + audit correctness |
| Groq-only in model_clients | Scope control |
| Safety rules in prompt_enhancer | Prevent hallucinated enhancements |

---

## Rejected Alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Keyword-only classifier (permanent) | Replaced by LLM classifier in M8 |
| Rule-only prompt enhancement (permanent) | Replaced by AI agent in M9; kept as fallback |
| LLM enhancement without fallback | Demo must work without Groq |
| Enhancing entire conversation history each turn | Cost + complexity |
| Separate OpenAI/Anthropic paths | Groq-only pivot |

---

## Decision Log (Chronological)

| Phase | Decision |
|-------|----------|
| 1 | Mock-first MVP, keyword routing |
| 2 | LiteLLM, Groq-only, YAML routing |
| 3 | Analytics schema, dashboard |
| 3A | Multi-turn memory |
| 3B | LLM classifier + keyword fallback |
| 4 | AI prompt engineering agent + rule fallback |
| 4 | enhancement_method in API; store enhanced_prompt in model_runs |
| 4 | Analytics history per model_run |
| Docs | Updated for v0.2.0 |
| Git | Pushed to github.com/Apatel468/smartllm-router |

---

## Questions for Future Review

1. Should enhancer model move to `models.yaml` (like classifier)?
2. Cache classification/enhancement for identical prompts?
3. Should `enhancement_method` be stored in SQLite?
4. When to rename `mock_response` → `response`?
5. Is 3 Groq calls per turn acceptable at scale?

Document answers here when decided.

---
