# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.2.2 · **Last updated:** June 2026

---

## Overview

TokenMaxx is a two-tier web application that optimizes LLM spend by routing each user prompt to an appropriate Groq model, enhancing prompts before inference, and reporting cost savings against a premium baseline.

---

## Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Frontend | React + Vite | Chat UI, analytics dashboard |
| API | FastAPI | `/chat`, `/conversations`, `/analytics` |
| Services | Python modules | Classify, enhance, route, generate, track cost |
| Data | SQLite | Conversations, messages, model runs |
| External | Groq via LiteLLM | LLM inference |

---

## Request Flow

```
User prompt
  → classify (keyword rules)
  → enhance prompt (Groq AI or rules)
  → route to model (models.yaml)
  → generate response (Groq)
  → clean response (strip thinking tags)
  → estimate costs vs GPT-4o baseline
  → persist turn + generate title (first reply)
  → return ChatResponse
```

---

## Data Model

- **conversations** — thread metadata + title
- **messages** — user (original) and assistant content
- **model_runs** — routing, tokens, costs, enhanced prompt metadata

---

## Configuration

All routing and pricing lives in `backend/config/models.yaml`:

- Task type → Groq model mapping
- Per-model token pricing
- Premium baseline for savings calculation

---

## Security Notes

- Single-user MVP — no authentication
- `GROQ_API_KEY` in `backend/.env` — never commit
- CORS limited to local dev ports (5173, 5174)

---

## Related Docs

- [architecture.md](architecture.md) — detailed technical reference
- [project_memory.md](project_memory.md) — full project context
