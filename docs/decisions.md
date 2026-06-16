# TokenMaxx — Architectural Decisions

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.3 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Backend | FastAPI | OpenAPI, Pydantic, async-ready |
| Database | SQLite | Zero setup for MVP |
| Auth | bcrypt + PyJWT (HS256) | Simple stateless tokens |
| LLM gateway | LiteLLM | Unified Groq interface |
| Provider | Groq only (allowlisted) | Cost/speed; controlled catalog |
| Frontend | React + Vite | Fast iteration |
| Model metadata | Python registry + allowlist | Curated scores; deployment control |
| Styling | Plain CSS | No UI framework dependency |
| Tests | pytest + httpx | FastAPI TestClient integration |

---

## Architectural Decisions

### Groq model allowlist (v0.3.2) 🔒
**Decision:** Only models in `GROQ_MODEL_ALLOWLIST` are synced, routed, and shown in Model Controls.  
**Chat:** 6 models. **Audio:** `whisper-large-v3` only (not chat-routable).  
**Why:** Predictable demo surface; no surprise models from Groq API; stale SQLite settings auto-pruned.

### LLM task classifier (v0.3.3) 🔒
**Decision:** `llm_classifier.py` classifies prompts via Groq `llama-3.1-8b-instant`; `prompt_analyzer.py` falls back to keyword rules on failure.  
**Returns:** `{ task_type, confidence, reason }` stored on `model_runs` and in `ChatResponse`.  
**Why:** More accurate task detection than keywords alone; cheap auxiliary model; graceful degradation.

### Task-aware routing (v0.3.3) 🔒
**Decision:** Replace fixed cost/speed-heavy scoring with complexity-aware dynamic weights + `TASK_MODEL_BONUSES`.  
**Simple prompts:** favor `llama-3.1-8b-instant` (low cost/latency).  
**Complex prompts:** favor capability models (`qwen/qwen3-32b`, `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`).  
**Fallback:** `openai/gpt-oss-20b` remains available but no longer dominates via cost/speed alone.  
**Why:** Old formula `(task×0.4)+(cost×0.2)+(speed×0.2)+(reasoning×0.2)` let gpt-oss-20b win almost every route.

### Routing debug metadata (v0.3.3)
**Decision:** `ChatResponse.top_candidate_scores` returns top 3 scored models; Latest Routing panel shows task, confidence, reason, and scores.  
**Why:** Transparent routing for demos and debugging without exposing full scorer internals.

### Client-side analytics export (v0.3.3)
**Decision:** CSV export built in browser from data already loaded on Analytics page (`exportAnalyticsReport.js`).  
**Filename:** `tokenmaxx-analytics-report.csv`. No new backend endpoint.  
**Why:** Zero server work; instant download for stakeholder demos; PDF deferred.

### On-demand model regenerate (v0.3.2) 🔒
**Decision:** `POST /chat/regenerate` — one LLM call when user clicks a top-5 chip.  
**Does not** pre-generate all candidates; reuses stored prompts; skips classify/enhance/route.  
**Why:** Avoids 5× token cost/latency; user-driven retry only.

### Optional prompt enhancement (v0.3.2)
**Decision:** User toggle `enhance_prompts` in `user_preferences`; `POST /chat` accepts `enhance_prompt` (default `true`).  
**When off:** `build_context()` skips enhancer Groq call.  
**Why:** User control over quality vs. cost/latency tradeoff.

### Prompt enhancement viewer (v0.3.3)
**Decision:** `PromptEnhancementViewer.jsx` shows original vs enhanced prompt below assistant replies (collapsible).  
**Why:** Transparency for demo; users see what the router actually sent to the model.

### Two-tier model enable/disable (v0.3.1) 🔒
**Rule:** `available = admin_enabled AND user_enabled`  
**Sync:** `user_model_settings.explicitly_set` distinguishes user intent from stale defaults.

### JWT stateless auth (v0.3.1)
Bearer JWT in `Authorization`; logout is client-side token discard.

### Analytics display vs. tracking (v0.3.2)
**Decision:** Enhancement and regeneration metrics stored in `model_runs` / summary API but **not shown** in Analytics dashboard KPI cards.  
**Why:** Cleaner stakeholder view focused on cost and savings.

### Message labels for multi-model turns (v0.3.2) 🔒
- Router reply: `response_label = "Router Selected"`
- User regenerate: `response_label = "User Selected Model"` + UI banner with model id
- Original router response preserved when user regenerates

### Cost baseline 🔒
GPT-4o rates from `models.yaml` → `premium_baseline` — illustrative.

### Original prompt preserved in DB 🔒
User `messages.content` = original text; `model_runs.enhanced_prompt` = what was sent to the model.

---

## Groq Touchpoints (with API key)

| Step | When | Model |
|------|------|-------|
| Classify | Each chat turn | `llm_classifier` → llama-3.1-8b-instant |
| Enhance | Each turn (if enabled) | `auxiliary.enhancer` (llama-3.1-8b-instant) |
| Route + respond | Each chat turn | Scored allowlisted model |
| Title | First turn | `auxiliary.title` |
| Regenerate | User click only | User-selected allowlisted model |

---

## Registry Score Caveat

Scores in `model_registry.py` are editorial estimates — not live Groq benchmarks. Task preference bonuses in `model_scorer.py` supplement registry scores for routing differentiation.
