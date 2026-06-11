# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.1

Use this script to demo TokenMaxx to stakeholders in 10–15 minutes.

---

## Setup (before the demo)

1. Start backend: `uvicorn main:app --reload --port 8001`
2. Start frontend: `npm run dev`
3. Open http://localhost:5173
4. Ensure `GROQ_API_KEY` and `JWT_SECRET` are set in `backend/.env`
5. Optional: set `ADMIN_EMAIL` / `ADMIN_PASSWORD` for a seeded admin account

---

## Act 1 — Intro & Login (1 minute)

> "This is **TokenMaxx** — Maximum Intelligence, Minimum Cost. Each user has their own account; admins can see org-wide usage."

1. Sign up or log in
2. Note the JWT session persists across refresh

---

## Act 2 — Simple Q&A (2 minutes)

**Prompt:** `What is machine learning in one paragraph?`

Highlight in the routing panel:

- Task type classified
- **Routing score** and **top candidates** list
- Model selected and savings %

---

## Act 3 — Model Controls (2–3 minutes)

Switch to **Model Controls** tab.

1. Show all routable Groq models with tiers and costs
2. **As admin:** disable a model org-wide — users see "Disabled by admin"
3. **As user:** toggle personal preferences among allowed models
4. Disable the top-scored model → send another chat → show **fallback** badge

---

## Act 4 — Coding task (2 minutes)

**Prompt:** `Write a Python function to check if a number is prime`

Show different model ranking (coding weights favor high `coding_score` models).

---

## Act 5 — Analytics (2 minutes)

Switch to **Analytics** tab.

- KPI cards (total chats, costs, savings) — scoped to logged-in user
- Model usage breakdown
- Recent conversations with per-turn costs

---

## Act 6 — Admin (optional, 2 minutes)

Log in as admin → **Admin** tab.

- Per-employee usage table: chats, tokens, cost, top models
- Tie back to enterprise cost visibility narrative

---

## Act 7 — API (optional, 1 minute)

Open http://127.0.0.1:8001/docs

- `POST /auth/login` → Bearer token
- `POST /chat` — `routing_score`, `candidate_models`
- `GET /model-settings` — Model Controls API
- `GET /admin/employee-usage` — admin only

---

## Closing

> "TokenMaxx scores the full Groq catalog, lets admins control what's allowed org-wide, lets each user fine-tune their preferences, and proves cost savings on every request — with per-user accountability."
