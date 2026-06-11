# TokenMaxx — Architectural Decisions

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.0 · **Last updated:** June 2026  
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
| Model metadata | Python registry | Rich scores; add models without router changes |
| Task weights | YAML task_profiles | Tune task matching without code deploy |
| Styling | Plain CSS | No UI framework dependency |

---

## Architectural Decisions

### Dynamic scoring router (v0.3.0) 🔒
**Decision:** Route by scoring all routable Groq models from `model_registry.py`, not a fixed YAML model map.  
**Formula:** `(task_match×0.4) + (cost×0.2) + (speed×0.2) + (reasoning×0.2)`  
**Why:** Supports full Groq catalog; users control enabled models via Model Controls.

### Model registry vs live API
**Decision:** `groq_models.py` merges Groq `GET /v1/models` with registry; logs models missing from registry.  
**Fallback:** Registry-only catalog when no API key.  
**Why:** Discover new Groq models automatically; curated scores stay in code.

### Model enable/disable in SQLite 🔒
**Decision:** `model_settings` table stores per-model `enabled` flag; router skips disabled models.  
**Fallback:** Next-highest enabled score; badge in UI if preferred model disabled.  
**Why:** User control without editing config files.

### Keyword classifier with optional LLM upgrade
**Decision:** Keyword rules classify `task_type` today.  
**Planned:** Groq LLM classifier as primary with keyword fallback.

### Auxiliary models in YAML
**Decision:** Enhancer, title, and classifier models in `models.yaml` → `auxiliary` block.  
**Why:** Small/fast models for non-routing calls; separate from scored chat models.

### Cost baseline 🔒
GPT-4o rates from `models.yaml` → `premium_baseline` — illustrative, not a live API call.

### Original prompt preserved in DB 🔒
User `messages.content` = original text; `model_runs.enhanced_prompt` = what was sent to the model.

---

## Groq Touchpoints (with API key)

| Step | File | When | Model |
|------|------|------|-------|
| Catalog sync | `groq_models.py` | Startup + `/models/sync` | API list |
| Enhance | `prompt_enhancer.py` | Every turn | `auxiliary.enhancer` |
| Route + respond | `router_engine` + `model_clients` | Every turn | Scored enabled model |
| Title | `conversation_title.py` | First turn | `auxiliary.title` |

---

## Registry Score Caveat

`reasoning_score`, `coding_score`, `writing_score`, and `avg_latency_ms` in `model_registry.py` are **editorial estimates** for routing — not live Groq benchmarks. Tune as needed.
