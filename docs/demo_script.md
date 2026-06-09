# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost

Use this script to demo TokenMaxx to stakeholders in 5–10 minutes.

---

## Setup (before the demo)

1. Start backend: `uvicorn main:app --reload --port 8001`
2. Start frontend: `npm run dev`
3. Open http://localhost:5173
4. Confirm header shows **TokenMaxx** and tagline **Maximum Intelligence, Minimum Cost**
5. Ensure `GROQ_API_KEY` is set in `backend/.env` for live responses

---

## Act 1 — Intro (30 seconds)

> "This is **TokenMaxx** — Maximum Intelligence, Minimum Cost. Instead of sending every request to an expensive model, TokenMaxx classifies the task, engineers the prompt, and routes to the right Groq model automatically."

Point out the header branding and footer tagline.

---

## Act 2 — Simple Q&A (2 minutes)

**Prompt:** `What is machine learning in one paragraph?`

Highlight in the routing panel:

- Task type classified
- Model selected (e.g. Groq Llama 3.1 8B)
- Actual cost vs premium baseline
- Savings percentage

> "A simple question doesn't need a premium model — TokenMaxx picked a fast, cheap option."

---

## Act 3 — Coding task (2 minutes)

**Prompt:** `Write a Python function to check if a number is prime`

Show:

- Different model routed (e.g. Qwen for coding)
- Enhanced prompt sent to the model (mention API returns this)
- Conversation title appears in sidebar after first reply

---

## Act 4 — Analytics (2 minutes)

Switch to **Analytics** tab.

Walk through:

- Total chats and costs
- Model usage breakdown
- Recent conversations with savings per turn

> "Every request is tracked — you can see exactly how much TokenMaxx saved versus always using GPT-4o."

---

## Act 5 — Multi-turn memory (1 minute)

Return to **Chat**, continue the coding conversation:

**Prompt:** `Add error handling to that function`

Show that context is preserved and routing/cost updates in the side panel.

---

## Closing (30 seconds)

> "TokenMaxx delivers maximum intelligence at minimum cost — smart routing, prompt engineering, and full visibility into savings. Questions?"

---

## Fallback (no API key)

If Groq is unavailable, explain that TokenMaxx falls back to rule-based enhancement and mock responses so the full pipeline still demos end-to-end.
