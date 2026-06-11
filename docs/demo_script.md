# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.0

Use this script to demo TokenMaxx to stakeholders in 8–12 minutes.

---

## Setup (before the demo)

1. Start backend: `uvicorn main:app --reload --port 8001`
2. Start frontend: `npm run dev`
3. Open http://localhost:5173
4. Ensure `GROQ_API_KEY` is set in `backend/.env`

---

## Act 1 — Intro (30 seconds)

> "This is **TokenMaxx** — Maximum Intelligence, Minimum Cost. It scores every Groq model for your task, picks the best enabled option, and tracks savings vs. always using premium."

---

## Act 2 — Simple Q&A (2 minutes)

**Prompt:** `What is machine learning in one paragraph?`

Highlight in the routing panel:

- Task type classified
- **Routing score** and **top candidates** list
- Model selected and savings %

---

## Act 3 — Model Controls (2 minutes)

Switch to **Model Controls** tab.

1. Show all routable Groq models with tiers and costs
2. Disable the top-scored model for a task type
3. Send another chat → show **"Preferred model disabled — fallback used"** badge

---

## Act 4 — Coding task (2 minutes)

**Prompt:** `Write a Python function to check if a number is prime`

Show different model ranking (coding weights favor high `coding_score` models).

---

## Act 5 — Analytics (2 minutes)

Switch to **Analytics** tab.

- KPI cards (total chats, costs, savings)
- Model usage breakdown (names wrap — no horizontal scroll)
- Recent conversations with per-turn costs

---

## Act 6 — API (optional, 1 minute)

Open http://127.0.0.1:8001/docs

- `POST /chat` — `routing_score`, `candidate_models`
- `GET /settings/models` — Model Controls API
- `GET /models/sync` — Groq catalog vs registry

---

## Closing

> "TokenMaxx doesn't lock you to three models — it scores the full Groq catalog, lets you control what's allowed, and proves cost savings on every request."
