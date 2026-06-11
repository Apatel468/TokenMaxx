# TokenMaxx — Architectural Decisions

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.1 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Backend | FastAPI | OpenAPI, Pydantic, async-ready |
| Database | SQLite | Zero setup for MVP |
| Auth | bcrypt + PyJWT (HS256) | Simple stateless tokens for demo/MVP |
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

### Two-tier model enable/disable (v0.3.1) 🔒
**Decision:** Split `model_settings` into `admin_model_settings` (org-wide) and `user_model_settings` (personal).  
**Effective rule:** `available = admin_enabled AND user_enabled`; missing rows default to enabled.  
**API:** Primary `GET/PUT /model-settings`; legacy `/settings/models` aliases retained.  
**Why:** Admins can disable models org-wide; users still choose among allowed models.

### JWT stateless auth (v0.3.1)
**Decision:** Bearer JWT in `Authorization` header; token stored in `localStorage` on the client.  
**No server sessions** — logout is client-side token discard.  
**Why:** Minimal infrastructure for MVP; easy FastAPI `Depends(get_current_user)` pattern.

### Per-user data isolation
**Decision:** `conversations.user_id` and `model_runs.user_id` scope all chat and analytics to the authenticated user.  
**Admin exception:** `GET /admin/employee-usage` aggregates across users (admin role only).

### Model registry vs live API
**Decision:** `groq_models.py` merges Groq `GET /v1/models` with registry; logs models missing from registry.  
**Fallback:** Registry-only catalog when no API key.  
**Why:** Discover new Groq models automatically; curated scores stay in code.

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
| Route + respond | `router_engine` + `model_clients` | Every turn | Scored available model |
| Title | `conversation_title.py` | First turn | `auxiliary.title` |

---

## Registry Score Caveat

`reasoning_score`, `coding_score`, `writing_score`, and `avg_latency_ms` in `model_registry.py` are **editorial estimates** for routing — not live Groq benchmarks. Tune as needed.
