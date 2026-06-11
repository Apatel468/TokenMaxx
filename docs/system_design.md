# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.1 · **Last updated:** June 2026

---

## Overview

TokenMaxx is a two-tier web application that optimizes LLM spend by scoring every available Groq model for each task, respecting org-wide and per-user enable/disable preferences, authenticating users with JWT, enhancing prompts before inference, and reporting cost savings against a premium baseline.

---

## Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Frontend | React + Vite | Auth UI, chat, analytics, model controls, admin dashboard |
| API | FastAPI | `/auth`, `/chat`, `/conversations`, `/analytics`, `/model-settings`, `/admin` |
| Services | Python modules | Auth, classify, enhance, score, route, generate, track cost |
| Data | SQLite | Users, conversations, messages, model runs, model settings |
| External | Groq via LiteLLM | LLM inference + model catalog API |

---

## Request Flow

```
User signs up / logs in → JWT stored client-side
User prompt [Bearer token]
  → authenticate user
  → classify (keyword rules)
  → enhance prompt (Groq AI or rules)
  → sync Groq catalog + filter available models (admin ∩ user prefs)
  → score all candidates (registry metadata + task profile)
  → pick highest-scoring available model
  → generate response (Groq)
  → clean response
  → estimate costs vs GPT-4o baseline
  → persist turn + title (first reply), scoped to user_id
  → return ChatResponse with score + candidates
```

---

## Configuration

| Source | Contents |
|--------|----------|
| `model_registry.py` | Model metadata, capability scores, pricing, latency |
| `models.yaml` | Task profile weights, auxiliary models, premium baseline |
| SQLite `admin_model_settings` | Org-wide enabled flag per model |
| SQLite `user_model_settings` | Per-user enabled flag per model |
| `.env` | `GROQ_API_KEY`, `JWT_SECRET`, `JWT_EXPIRE_HOURS`, optional admin seed |

**Adding a new Groq model:** add entry to `model_registry.py` — router code unchanged.

---

## Security Notes

- **JWT authentication** — bcrypt passwords; HS256 Bearer tokens on protected routes
- **Role-based access** — `admin` role for `/admin/*`; users see only their own chats
- **Model Controls** — admins control org-wide availability; users cannot re-enable admin-disabled models
- `GROQ_API_KEY` and `JWT_SECRET` in `backend/.env` — never commit
- CORS limited to local dev ports (5173, 5174)
- Stateless JWT — no server-side session store or token revocation list (MVP)

---

## Related Docs

- [architecture.md](architecture.md) — detailed technical reference
- [project_memory.md](project_memory.md) — full project context
- [decisions.md](decisions.md) — design decisions
