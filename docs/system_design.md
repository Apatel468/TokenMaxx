# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.2 · **Last updated:** June 2026

---

## Overview

TokenMaxx is a two-tier web application that optimizes LLM spend by scoring allowlisted Groq chat models per task, respecting org-wide and per-user toggles, optionally enhancing prompts, letting users regenerate with another model on demand, and reporting savings vs. a GPT-4o baseline.

---

## Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Frontend | React + Vite | Auth, chat, regenerate UI, analytics, settings |
| API | FastAPI | `/auth`, `/chat`, `/chat/regenerate`, `/user/preferences`, `/model-settings` |
| Services | Python | Classify, enhance (optional), score, route, regenerate, track cost |
| Data | SQLite | Users, preferences, conversations, model runs, settings |
| External | Groq via LiteLLM | Inference on allowlisted models |

---

## Request Flow (new chat)

```
Login → JWT stored
POST /chat { prompt, enhance_prompt? }
  → classify (keywords)
  → enhance if user preference enabled
  → score allowlisted available models
  → pick best → generate → persist ("Router Selected")
  → return top_recommendations for UI chips
```

## Request Flow (regenerate)

```
User clicks model chip in routing panel
POST /chat/regenerate { conversation_id, message_id, model_id }
  → reuse stored prompts (no classify/enhance/route)
  → single generate call
  → append message: "User switched model to …"
```

---

## Configuration

| Source | Contents |
|--------|----------|
| `model_registry.py` | `GROQ_MODEL_ALLOWLIST`, metadata, scores, pricing |
| `models.yaml` | Task profiles, auxiliary models, premium baseline |
| SQLite settings | Admin + user model toggles |
| SQLite `user_preferences` | `enhance_prompts` boolean |

**Changing models:** edit `GROQ_MODEL_ALLOWLIST` in `model_registry.py`; stale SQLite rows auto-cleaned on startup.

---

## Security Notes

- JWT auth on all protected routes; admin role for `/admin/*`
- Model Controls gate regenerate and routing (`admin_enabled AND user_enabled`)
- Secrets in `.env` only — never commit
- CORS: localhost 5173/5174

---

## Analytics

- **Displayed:** total chats, costs, savings %, model usage, recent history
- **Tracked but hidden in UI:** enhancement enabled/disabled counts, enhancer cost saved, regeneration count (available via API/DB for future use)
- **Historical runs** with deprecated model ids remain readable; costs stored at request time

---

## Related Docs

- [architecture.md](architecture.md) — detailed technical reference
- [project_memory.md](project_memory.md) — full project context
- [decisions.md](decisions.md) — design decisions
