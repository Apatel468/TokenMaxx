# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.0 · **Last updated:** June 2026

---

## Overview

TokenMaxx is a two-tier web application that optimizes LLM spend by scoring every available Groq model for each task, respecting user enable/disable preferences, enhancing prompts before inference, and reporting cost savings against a premium baseline.

---

## Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Frontend | React + Vite | Chat, analytics, model controls |
| API | FastAPI | `/chat`, `/conversations`, `/analytics`, `/settings`, `/models` |
| Services | Python modules | Classify, enhance, score, route, generate, track cost |
| Data | SQLite | Conversations, messages, model runs, model settings |
| External | Groq via LiteLLM | LLM inference + model catalog API |

---

## Request Flow

```
User prompt
  → classify (keyword rules)
  → enhance prompt (Groq AI or rules)
  → sync Groq catalog + filter enabled models
  → score all candidates (registry metadata + task profile)
  → pick highest-scoring enabled model
  → generate response (Groq)
  → clean response
  → estimate costs vs GPT-4o baseline
  → persist turn + title (first reply)
  → return ChatResponse with score + candidates
```

---

## Configuration

| Source | Contents |
|--------|----------|
| `model_registry.py` | Model metadata, capability scores, pricing, latency |
| `models.yaml` | Task profile weights, auxiliary models, premium baseline |
| SQLite `model_settings` | Per-model enabled flag |

**Adding a new Groq model:** add entry to `model_registry.py` — router code unchanged.

---

## Security Notes

- Single-user MVP — no authentication
- `GROQ_API_KEY` in `backend/.env` — never commit
- CORS limited to local dev ports (5173, 5174)

---

## Related Docs

- [architecture.md](architecture.md) — detailed technical reference
- [project_memory.md](project_memory.md) — full project context
- [decisions.md](decisions.md) — design decisions
