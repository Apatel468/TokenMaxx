# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.4.0

Use this script to demo TokenMaxx to stakeholders in 18–22 minutes.

---

## Setup (before the demo)

1. Start backend: `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Set `GROQ_API_KEY` and `JWT_SECRET` in `backend/.env`

---

## Act 1 — Intro & Login (1 minute)

> "TokenMaxx classifies each prompt, intelligently enhances it, routes to the best allowed Groq model, streams the answer live, and tracks savings vs. premium."

1. Sign up or log in
2. Session persists across refresh (JWT)

---

## Act 2 — Streaming + Simple Q&A (2 minutes)

**Prompt:** `What is photosynthesis?`

Watch the assistant reply **appear token-by-token** (typing cursor).

Highlight **Latest Routing** (updates when routing completes, before tokens finish):

- Task type, confidence, selected model (`llama-3.1-8b-instant` likely)
- Top 3 candidate scores
- Savings %

---

## Act 3 — Task-Aware Routing (3 minutes)

| Prompt | Expected model |
|--------|----------------|
| `Debug this React component that throws a hooks error` | `qwen/qwen3-32b` |
| `Write a professional business report on Q3 revenue` | `llama-3.3-70b-versatile` or `llama-4-scout` |
| `Solve this complex logic puzzle step by step` | `openai/gpt-oss-120b` |

---

## Act 4 — Prompt Intelligence v2 (2 minutes)

1. Expand **View Prompt Optimization** below an assistant reply
2. Show: **Enhanced Prompt**, **Task Type**, **Complexity Level**, **Persona**, **Enhancement Strategy**
3. Compare a simple Q&A (minimal enhancement) vs. a complex coding/business prompt (full specification)
4. Note: no internal bracket notes like `[Original user request — preserve this intent: ...]`

---

## Act 5 — Model Regenerate (2 minutes)

1. Click a different top-5 model chip
2. Show **User switched model to "…"** banner
3. Emphasize: one API call per click, not all 5 upfront (regenerate is non-streaming)

---

## Act 6 — Model Controls (2 minutes)

- Six allowlisted models + **Prompt Enhancement** toggle
- Admin org-wide disable → chip shows disabled reason
- User personal toggles

---

## Act 7 — Analytics & Export (2 minutes)

- KPIs: Total Chats, Actual/Premium Cost, Savings %
- Model usage breakdown
- **Export Report** → `tokenmaxx-analytics-report.csv`

---

## Act 8 — API (optional, 1 minute)

http://127.0.0.1:8001/docs

- `POST /chat/stream` — SSE events
- `POST /chat` — sync (tests)
- `POST /chat/regenerate`
- Response includes `prompt_analysis`

---

## Closing

> "TokenMaxx classifies every request, enhances prompts with task-aware intelligence, streams responses live, routes six curated Groq models with transparent scoring, respects admin and user preferences, regenerates on demand, exports analytics for stakeholders, and proves savings on every request."
