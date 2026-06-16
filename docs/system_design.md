# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.3 · **Last updated:** June 2026

---

## Overview

TokenMaxx is a two-tier web application that optimizes LLM spend by classifying prompts with an LLM, scoring allowlisted Groq chat models per task with complexity-aware weights, respecting org-wide and per-user toggles, optionally enhancing prompts, letting users regenerate with another model on demand, exporting analytics for demos, and reporting savings vs. a GPT-4o baseline.

---

## Components

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Frontend | React + Vite | Auth, chat, routing debug UI, analytics export, settings |
| API | FastAPI | `/auth`, `/chat`, `/chat/regenerate`, `/user/preferences`, `/model-settings`, `/analytics/*` |
| Services | Python | LLM classify, enhance (optional), complexity-aware score, route, regenerate, track cost |
| Data | SQLite | Users, preferences, conversations, model runs, settings |
| External | Groq via LiteLLM | Inference on allowlisted models |

---

## Request Flow (new chat)

```
Login → JWT stored
POST /chat { prompt, enhance_prompt? }
  → LLM classify (keyword fallback)
  → enhance if user preference enabled
  → compute complexity → score allowlisted available models
  → pick best → generate → persist ("Router Selected")
  → return top_recommendations + top_candidate_scores + classification metadata
```

## Request Flow (regenerate)

```
User clicks model chip in routing panel
POST /chat/regenerate { conversation_id, message_id, model_id }
  → reuse stored prompts (no classify/enhance/route)
  → single generate call
  → append message: "User switched model to …"
```

## Analytics Export Flow (client-side)

```
Analytics tab loads summary + model-usage + history (existing API calls)
User clicks "Export Report"
  → exportAnalyticsReport.js builds CSV from in-memory state
  → browser downloads tokenmaxx-analytics-report.csv
```

No new backend endpoint required.

---

## Configuration

| Source | Contents |
|--------|----------|
| `model_registry.py` | `GROQ_MODEL_ALLOWLIST`, metadata, scores, pricing |
| `models.yaml` | Task profiles, auxiliary models, premium baseline |
| `model_scorer.py` | `TASK_MODEL_BONUSES`, complexity keywords, dynamic weights |
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

- **Displayed:** total chats, costs, savings %, model usage, recent history, CSV export
- **Export contents:** summary KPIs, model usage breakdown, recent conversations
- **Tracked but hidden in UI:** enhancement enabled/disabled counts, enhancer cost saved, regeneration count (available via API/DB for future use)
- **Historical runs** with deprecated model ids remain readable; costs stored at request time

---

## Related Docs

- [architecture.md](architecture.md) — detailed technical reference
- [project_memory.md](project_memory.md) — full project context
- [decisions.md](decisions.md) — design decisions
- [demo_script.md](demo_script.md) — stakeholder demo walkthrough
