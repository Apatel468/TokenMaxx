# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.4.0 · **Last updated:** June 2026

---

## Overview

TokenMaxx is a two-tier web application that optimizes LLM spend by classifying prompts, analyzing and enhancing them with Prompt Intelligence v2, scoring allowlisted Groq models per task, streaming responses over SSE, respecting org-wide and per-user toggles, supporting on-demand regeneration, exporting analytics, and reporting savings vs. a GPT-4o baseline.

---

## Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Frontend | React + Vite | Auth, SSE chat, routing UI, prompt optimization viewer, analytics export |
| API | FastAPI | `/auth`, `/chat`, `/chat/stream`, `/chat/regenerate`, `/analytics/*` |
| Services | Python | Classify, Prompt Intelligence v2, route, stream/sync generate, persist |
| Data | SQLite | Users, preferences, conversations, model runs, settings |
| External | Groq via LiteLLM | Inference + streaming on allowlisted models |

---

## Request Flow (new chat — streaming, default UI)

```
Login → JWT stored
POST /chat/stream { prompt, enhance_prompt? }
  → LLM classify (keyword fallback)
  → Prompt Intelligence v2 (if enhancement ON)
  → route to best available model
  → SSE: routing_complete (metadata for Latest Routing)
  → stream tokens live
  → persist after complete → SSE: complete (full ChatResponse + prompt_analysis)
```

## Request Flow (regenerate)

```
POST /chat/regenerate { conversation_id, message_id, model_id }
  → reuse stored prompts (no classify/enhance/route)
  → single non-streaming generate call
```

## Analytics Export Flow

```
Analytics tab → existing API data in memory
Export Report → tokenmaxx-analytics-report.csv (client-side, no new endpoint)
```

---

## Configuration

| Source | Contents |
|--------|----------|
| `model_registry.py` | `GROQ_MODEL_ALLOWLIST`, metadata, pricing |
| `models.yaml` | Task profiles, auxiliary models, premium baseline |
| `model_scorer.py` | `TASK_MODEL_BONUSES`, routing complexity weights |
| `prompt_intelligence.py` | Personas, enhancement strategies, complexity scoring |
| SQLite | Model toggles, `enhance_prompts` |

---

## Security Notes

- JWT on all protected routes; admin role for `/admin/*`
- Model availability: `admin_enabled AND user_enabled`
- Secrets in `.env` only — never commit
- CORS: localhost 5173/5174

---

## Related Docs

- [architecture.md](architecture.md) — detailed technical reference
- [project_memory.md](project_memory.md) — full project context
- [decisions.md](decisions.md) — design decisions
- [demo_script.md](demo_script.md) — stakeholder demo walkthrough
