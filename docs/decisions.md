# SmartLLM Router — Architectural Decisions

> Record of major decisions, tradeoffs, and rules for future developers.  
> **Version:** 0.2.1 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Backend | FastAPI | Async-ready, OpenAPI, Pydantic validation |
| Database | SQLite | Zero setup for MVP/demo |
| LLM gateway | LiteLLM | Unified Groq interface; easy multi-provider later |
| Provider | Groq only | Cost/speed focus for demo |
| Frontend | React + Vite | Fast dev, component model |
| Config | YAML | Routing changes without code deploy |
| Styling | Plain CSS | No extra dependencies |

---

## Architectural Decisions

### Service layer between routers and persistence 🔒
Business logic in `backend/services/`; routers orchestrate only.

### LLM classifier with keyword fallback (Phase 3B)
**Decision:** Primary classification via Groq `llama-3.1-8b-instant` + LiteLLM JSON mode; keyword rules as fallback.  
**Why:** More accurate task routing than keywords alone; still works offline without API key.  
**Tradeoff:** Extra Groq call (+latency, +cost) on every chat request.  
**Config:** `models.yaml` → `classifier` block; allowed types from `models` keys.  
**Status (June 2026):** Keyword-only code in `prompt_analyzer.py` — LLM path needs restore; `context_builder` still expects `difficulty` and `risk_level`.

### AI Prompt Engineering Agent with rule fallback (Phase 4)
**Decision:** Primary enhancement via Groq `llama-3.1-8b-instant` returning JSON (`enhanced_prompt`, `system_prompt`, `enhancement_reason`); rule templates as fallback.  
**Why:** Smarter prompt wrapping than static templates; preserves user intent with explicit safety rules in agent prompt.  
**Tradeoff:** Groq call per request.  
**Model location:** Hardcoded `ENHANCER_MODEL` in `prompt_enhancer.py`.  
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

### Conversation titles after first assistant reply (M11)
**Decision:** Generate title from **both** first user message and first assistant response — not from user prompt alone.  
**Why:** User-only titles became keyword soup; assistant reply clarifies actual topic.  
**Rules:** 3–8 words, ChatGPT-style; store in `conversations.title` once; never regenerate if set.  
**AI:** Groq `llama-3.1-8b-instant` on new chat first turn.  
**List backfill:** Rule-based only (`use_ai=False`) when loading sidebar to avoid Groq rate limits on bulk reads.  
**Placeholder:** `"New Chat"` until first reply completes.

### Response cleanup before storage
**Decision:** `response_cleaner.py` strips `<think>` from model output (Qwen).  
**Why:** Users should not see internal chain-of-thought tags in chat or analytics.

### GPT-4o as savings baseline 🔒
Illustrative savings vs premium — not a live OpenAI call.

### Mock fallback on final response
**Decision:** Missing key → keyword classify, rule enhance, rule title, mock chat response.  
**Why:** Demo still works end-to-end without Groq.

### Analytics per `model_run`
**Decision:** `GET /analytics/history` iterates `model_runs`, not one row per conversation.  
**Why:** Multi-turn threads produce multiple turns; each includes `enhanced_prompt`.

### Schema migration via startup ALTER
**Decision:** `database._migrate_*_columns()` adds columns to existing SQLite DBs on startup.  
**Why:** No Alembic yet; `create_all` doesn't alter existing tables.  
**Tradeoff:** Fragile for production — migrate to Alembic before deploy 🔒.

---

## Assumptions

1. Single user / no auth
2. English prompts (enhancer + title tuned for English)
3. One shared `GROQ_API_KEY`
4. ~4 chars/token when usage missing
5. Multiple Groq calls per chat acceptable for MVP demo cost

---

## Important Implementation Notes

### Environment variables
- `GROQ_API_KEY` — used by `prompt_enhancer`, `conversation_title`, `model_clients`
- **🔒 NEVER read, log, or commit `.env` contents**

### LiteLLM model strings
```
llama-3.1-8b-instant  →  groq/llama-3.1-8b-instant
qwen/qwen3-32b        →  groq/qwen/qwen3-32b
```

### Groq touchpoints per request (with API key)

| Step | File | When | Model |
|------|------|------|-------|
| Classify | `prompt_analyzer.py` | Every turn (planned) | classifier from YAML |
| Enhance | `prompt_enhancer.py` | Every turn | 8B instant |
| Respond | `model_clients.py` | Every turn | routed from YAML |
| Title | `conversation_title.py` | First turn only | 8B instant |

### Config cache
Restart uvicorn after editing `models.yaml`.

### Response field naming debt
- `ChatResponse.mock_response` — holds real Groq text too (legacy name)
- Plan rename in M12

### Prompt comparison (original vs enhanced)
Not a separate analyzer module. Comparison data lives in:
- `prompt_enhancer.py` — produces `enhanced_prompt`
- `POST /chat` response — returns `original_prompt` + `enhanced_prompt`
- `model_runs.enhanced_prompt` — persisted for analytics history

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
| Title generated once rule | Sidebar/history consistency |

---

## Rejected Alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Title from user prompt only | Produced keyword soup |
| Title on conversation create | No assistant context yet |
| Keyword-only classifier (permanent) | Replaced by LLM classifier in M8 design |
| Rule-only prompt enhancement (permanent) | Replaced by AI agent in M9; kept as fallback |
| LLM enhancement without fallback | Demo must work without Groq |
| Enhancing entire conversation history each turn | Cost + complexity |
| Separate OpenAI/Anthropic paths | Groq-only pivot |
| AI title backfill on every list load | Groq rate limits |

---

## Decision Log (Chronological)

| Phase | Decision |
|-------|----------|
| 1 | Mock-first MVP, keyword routing |
| 2 | LiteLLM, Groq-only, YAML routing |
| 3 | Analytics schema, dashboard |
| 3A | Multi-turn memory |
| 3B | LLM classifier + keyword fallback (design) |
| 4 | AI prompt engineering agent + rule fallback |
| 4 | enhancement_method in API; store enhanced_prompt in model_runs |
| 4 | Analytics history per model_run |
| 4+ | Response cleaner for Qwen thinking tags |
| 4+ | Conversation titles from first exchange (user + assistant) |
| 4+ | 100vh UI, 3-column chat, analytics polish |
| Docs | Updated for v0.2.1 |
| Git | github.com/Apatel468/smartllm-router |

---

## Questions for Future Review

1. Restore LLM classifier in `prompt_analyzer.py` or use keyword-only with default difficulty/risk?
2. Should enhancer + title models move to `models.yaml`?
3. Cache classification/enhancement for identical prompts?
4. Should `enhancement_method` be stored in SQLite?
5. When to rename `mock_response` → `response`?
6. Optional endpoint to regenerate titles for legacy conversations?

Document answers here when decided.

---
