# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.3

Use this script to demo TokenMaxx to stakeholders in 15–20 minutes.

---

## Setup (before the demo)

1. Start backend: `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Set `GROQ_API_KEY` and `JWT_SECRET` in `backend/.env`
5. Optional: `ADMIN_EMAIL` / `ADMIN_PASSWORD` for admin account

---

## Act 1 — Intro & Login (1 minute)

> "TokenMaxx classifies each prompt, routes it to the best **allowed** Groq model for that task, tracks savings vs. premium, and lets users retry with a different model on demand."

1. Sign up or log in
2. Session persists across refresh (JWT)

---

## Act 2 — Simple Q&A (2 minutes)

**Prompt:** `What is photosynthesis?`

Highlight **Latest Routing** panel:

- Task type: `general_qa`
- Classification confidence + reason
- Selected model: likely `llama-3.1-8b-instant` (cheap, fast, right-sized)
- **Top 3 candidate scores** — show why the winner beat alternatives
- Savings %

> "Simple questions don't need an expensive model. The router picks the right tool for the job."

---

## Act 3 — Task-Aware Routing (3 minutes)

Send three different prompts and compare routing:

| Prompt | Expected task | Expected model |
|--------|---------------|----------------|
| `Debug this React component that throws a hooks error` | coding | `qwen/qwen3-32b` |
| `Write a professional business report on Q3 revenue` | report | `llama-3.3-70b-versatile` or `llama-4-scout` |
| `Solve this complex logic puzzle step by step` | reasoning | `openai/gpt-oss-120b` |

Point out how task type, confidence, and top-3 scores change each time.

---

## Act 4 — Model Regenerate (2 minutes)

1. Click a **different** top-5 model chip (not the router's pick)
2. Show new assistant message: **User switched model to "…"**
3. Original **Router Selected** response still visible above
4. Emphasize: only **one** extra API call — not all 5 models upfront

---

## Act 5 — Prompt Enhancement (1–2 minutes)

1. Expand **Prompt Enhancement** viewer below an assistant reply
2. Show original user prompt vs. enhanced prompt sent to the model
3. In **Model Controls**, toggle **Prompt Enhancement** OFF
4. Send another message — note one fewer Groq call

---

## Act 6 — Model Controls (2 minutes)

**Model Controls** tab:

1. Six allowlisted chat models with tiers and costs
2. **Prompt Enhancement** toggle
3. Admin: disable a model org-wide → chip shows "Disabled by administrator"
4. User: personal toggles on allowed models

---

## Act 7 — Analytics & Export (2 minutes)

**Analytics** tab — KPIs: Total Chats, Actual Cost, Premium Cost, Total Savings, Savings %.

- Model usage breakdown
- Recent conversations with per-turn costs
- Click **Export Report** → downloads `tokenmaxx-analytics-report.csv`

> "One click gives you a shareable report for stakeholders — no extra API calls."

---

## Act 8 — Admin (optional, 2 minutes)

**Admin** tab — per-employee usage, top models, cost totals.

---

## Act 9 — API (optional, 1 minute)

http://127.0.0.1:8001/docs

- `POST /chat` — `top_recommendations`, `top_candidate_scores`, `classification_confidence`
- `POST /chat/regenerate`
- `GET /model-settings`, `GET /user/preferences`

---

## Closing

> "TokenMaxx classifies every request, scores six curated Groq models with task-specific intelligence, respects admin and user preferences, optionally enhances prompts, regenerates on demand without wasting tokens, exports analytics for demos, and proves savings on every request."
