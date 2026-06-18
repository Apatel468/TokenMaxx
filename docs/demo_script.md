# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.6.0

Use this script to demo TokenMaxx to stakeholders in 24–30 minutes.

---

## Setup (before the demo)

1. Start backend: `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Set API keys in `backend/.env`:
   - `GROQ_API_KEY` — required for classifier, enhancer, and Groq models
   - `OPENAI_API_KEY` — optional; enables GPT-4o / o3-mini routing demos
   - `ANTHROPIC_API_KEY` — optional; enables Claude routing demos
5. Set `JWT_SECRET`
6. (Optional) Upload a sample `.md` or `.txt` file in **Documents** for RAG demo

---

## Act 1 — Intro & Login (1 minute)

> "TokenMaxx classifies each prompt, intelligently enhances it, retrieves context from your documents, routes to the best allowed model across Groq, OpenAI, and Anthropic, streams the answer live, and tracks savings vs. premium."

1. Sign up or log in
2. Session persists across refresh (JWT)

---

## Act 2 — Streaming + Simple Q&A (2 minutes)

**Prompt:** `What is photosynthesis?`

Watch the assistant reply **appear token-by-token** (typing cursor).

Highlight **Latest Routing** (updates when routing completes, before tokens finish):

- Task type, confidence, selected model (`llama-3.1-8b-instant` likely on Groq)
- Provider availability chips (groq / openai / anthropic)
- Top 3 candidate scores
- Savings %

---

## Act 3 — Task-Aware Routing (4 minutes)

| Prompt | Expected model |
|--------|----------------|
| `Debug this React component that throws a hooks error` | `qwen/qwen3-32b` (Groq) or `gpt-4o` / `claude-3-5-sonnet` if premium keys set |
| `Write a professional business report on Q3 revenue` | `claude-3-5-sonnet` or `gpt-4o` (premium) or `llama-3.3-70b-versatile` (Groq) |
| `Solve this complex logic puzzle step by step` | `openai/gpt-oss-120b` or `o3-mini` |

Point out that routing only considers providers with configured API keys.

---

## Act 4 — Prompt Intelligence v2 (2 minutes)

1. Expand **View Prompt Optimization** below an assistant reply
2. Show: **Enhanced Prompt**, **Task Type**, **Complexity Level**, **Persona**, **Enhancement Strategy**
3. Compare a simple Q&A (minimal enhancement) vs. a complex coding/business prompt (full specification)
4. Note: no internal bracket notes like `[Original user request — preserve this intent: ...]`

---

## Act 5 — RAG Documents (3 minutes)

1. Open **Documents** tab
2. Upload a company FAQ or product spec (TXT/MD/PDF)
3. Return to **Chat** and ask a question answerable only from that file
4. Point out the **RAG badge** showing source filenames
5. Explain: chunks retrieved from ChromaDB, injected into system prompt before routing

---

## Act 6 — Model Regenerate (2 minutes)

1. Click a different top-5 model chip
2. Show **User switched model to "…"** banner
3. Emphasize: one API call per click, not all 5 upfront (regenerate is non-streaming)

---

## Act 7 — Model Controls & API Keys (2 minutes)

- Eleven allowlisted chat models across three providers + **Prompt Enhancement** toggle
- Admin org-wide disable → chip shows disabled reason
- User personal toggles
- **API Keys:** add personal Groq, OpenAI, or Anthropic keys; user key overrides app key for that provider

---

## Act 8 — Activity Logs (1 minute)

1. Open **Logs** tab
2. Show recent events: chat routing, RAG retrieval, model calls
3. Note: admins can see all users' logs via **Admin** → logs

---

## Act 9 — Analytics & Export (2 minutes)

- KPIs: Total Chats, Actual/Premium Cost, Savings %
- Model usage breakdown
- Provider usage breakdown (Groq vs OpenAI vs Anthropic)
- **Export Report** → `tokenmaxx-analytics-report.csv`

---

## Act 10 — API (optional, 1 minute)

http://127.0.0.1:8001/docs

- `POST /chat/stream` — SSE events (includes provider + RAG metadata)
- `POST /chat` — sync (tests)
- `POST /documents/upload` — RAG ingestion
- `GET /logs/my` — activity logs
- `GET /analytics/provider-usage` — provider breakdown
- `POST /user/api-keys` — encrypted key storage

---

## Closing

> "TokenMaxx classifies every request, enhances prompts with task-aware intelligence, grounds answers in your uploaded documents, streams responses live, routes eleven curated models across Groq, OpenAI, and Anthropic with transparent scoring and provider-key awareness, supports per-user API keys, logs every pipeline step, respects admin and user preferences, regenerates on demand, exports analytics for stakeholders, and proves savings on every request."
