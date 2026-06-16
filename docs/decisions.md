# TokenMaxx — Architectural Decisions

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.4.0 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Backend | FastAPI | OpenAPI, Pydantic, `StreamingResponse` for SSE |
| Database | SQLite | Zero setup for MVP |
| Auth | bcrypt + PyJWT (HS256) | Simple stateless tokens |
| LLM gateway | LiteLLM | Unified Groq interface + `stream=True` |
| Streaming | Server-Sent Events | `POST /chat/stream`; frontend uses fetch + ReadableStream |
| Provider | Groq only (allowlisted) | Cost/speed; controlled catalog |
| Frontend | React + Vite | Fast iteration |
| Tests | pytest + httpx | 39 tests; mocked LLM/stream in CI |

---

## Architectural Decisions

### Groq model allowlist (v0.3.2) 🔒
**Decision:** Only models in `GROQ_MODEL_ALLOWLIST` are synced, routed, and shown in Model Controls.  
**Chat:** 6 models. **Audio:** `whisper-large-v3` only (not chat-routable).

### SSE streaming chat (v0.4.0) 🔒
**Decision:** `POST /chat/stream` returns `text/event-stream` with events: `routing_start`, `routing_complete`, `token`, `complete`, `error`.  
**Frontend default:** `streamChat()` in `api/chat.js`; `POST /chat` kept for sync/tests.  
**Persistence:** Assistant message saved only after stream completes.  
**Fallback:** Word-by-word fake stream when Groq streaming unavailable.  
**Why:** Live token display for demos; routing metadata arrives before tokens.

### Prompt Intelligence Engine v2 (v0.4.0) 🔒
**Decision:** `prompt_intelligence.py` analyzes then enhances — not just rewrite.  
**Outputs:** `PromptAnalysis` with task_type, complexity_score (0–100), complexity_level, persona, output_format, enhancement_strategy, enhanced_prompt.  
**Complexity tiers:** simple → minimal; medium → structured; complex → full specification.  
**Clean prompts:** No `[Original user request — preserve this intent: ...]` in stored or displayed text.  
**Why:** Task- and complexity-aware enhancement; transparent metadata for demos.

### LLM task classifier (v0.3.3) 🔒
**Decision:** `llm_classifier.py` + keyword fallback in `prompt_analyzer.py`.  
**Note:** Classifier task types (routing) differ from enhancement task types (v2 normalization).

### Task-aware routing (v0.3.3) 🔒
**Decision:** Complexity-aware dynamic weights + `TASK_MODEL_BONUSES` in `model_scorer.py`.

### Client-side analytics export (v0.3.3)
**Decision:** `tokenmaxx-analytics-report.csv` from in-memory Analytics data; no backend endpoint.

### On-demand model regenerate (v0.3.2) 🔒
**Decision:** One LLM call per chip click; reuses stored prompts; **non-streaming**.

### Optional prompt enhancement (v0.3.2)
**Decision:** User toggle `enhance_prompts`; when off, `build_disabled_analysis()` skips enhancer Groq call.

### Two-tier model enable/disable (v0.3.1) 🔒
**Rule:** `available = admin_enabled AND user_enabled`

### Original prompt preserved in DB 🔒
User `messages.content` = original text; `model_runs.enhanced_prompt` = clean enhanced text sent to model.

---

## Groq Touchpoints (with API key)

| Step | When | Model |
|------|------|-------|
| Classify | Each chat turn | `llm_classifier` → llama-3.1-8b-instant |
| Analyze + enhance | Each turn (if enabled) | Prompt Intelligence v2 → llama-3.1-8b-instant |
| Route + respond | Each chat turn | Scored allowlisted model (stream or sync) |
| Title | First turn | `auxiliary.title` |
| Regenerate | User click only | User-selected model (sync) |

---

## Registry Score Caveat

Scores in `model_registry.py` are editorial estimates. Routing uses `model_scorer.py` bonuses; enhancement uses `prompt_intelligence.py` personas and strategies.
