# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.2

Use this script to demo TokenMaxx to stakeholders in 12–18 minutes.

---

## Setup (before the demo)

1. Start backend: `uvicorn main:app --reload --port 8001`
2. Start frontend: `npm run dev`
3. Open http://localhost:5173
4. Set `GROQ_API_KEY` and `JWT_SECRET` in `backend/.env`
5. Optional: `ADMIN_EMAIL` / `ADMIN_PASSWORD` for admin account

---

## Act 1 — Intro & Login (1 minute)

> "TokenMaxx routes each prompt to the best **allowed** Groq model for the task, tracks savings vs. premium, and lets users retry with a different model on demand."

1. Sign up or log in
2. Session persists across refresh (JWT)

---

## Act 2 — Simple Q&A (2 minutes)

**Prompt:** `What is machine learning in one paragraph?`

Highlight routing panel:

- Task type, routing score, selected model
- **Top 5 model chips** — metadata only until clicked
- Savings %

---

## Act 3 — Model Regenerate (2 minutes)

1. Click a **different** top-5 model chip (not the router's pick)
2. Show new assistant message: **User switched model to "…"**
3. Original **Router Selected** response still visible above
4. Emphasize: only **one** extra API call — not all 5 models upfront

---

## Act 4 — Model Controls & Enhancement (2–3 minutes)

**Model Controls** tab:

1. Six allowlisted chat models with tiers and costs
2. **Prompt Enhancement** toggle — ON improves prompts (extra Groq call); OFF saves cost
3. Admin: disable a model org-wide → chip shows "Disabled by administrator"
4. User: personal toggles on allowed models

---

## Act 5 — Coding task (2 minutes)

**Prompt:** `Write a Python function to check if a number is prime`

Show coding-weighted ranking may pick `qwen/qwen3-32b`.

---

## Act 6 — Analytics (2 minutes)

**Analytics** tab — KPIs: Total Chats, Actual Cost, Premium Cost, Total Savings, Savings %.

- Model usage breakdown
- Recent conversations with per-turn costs

---

## Act 7 — Admin (optional, 2 minutes)

**Admin** tab — per-employee usage, top models, cost totals.

---

## Act 8 — API (optional, 1 minute)

http://127.0.0.1:8001/docs

- `POST /chat` — `top_recommendations`, `enhance_prompt`
- `POST /chat/regenerate`
- `GET /model-settings`, `GET /user/preferences`

---

## Closing

> "TokenMaxx scores six curated Groq models, respects admin and user preferences, optionally enhances prompts, regenerates on demand without wasting tokens, and proves savings on every request."
