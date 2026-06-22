# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.7.0

Use this script to demo TokenMaxx to stakeholders in 28–35 minutes.

---

## Setup (before the demo)

1. Start backend: `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Set API keys in `backend/.env`:
   - `GROQ_API_KEY` — classifier, enhancer, Groq models, document content
   - `OPENAI_API_KEY` — optional; GPT-4o routing + DALL-E images
   - `ANTHROPIC_API_KEY` — optional; Claude routing
5. Set `JWT_SECRET`
6. (Optional) Upload a sample file in **Documents** for RAG demo

---

## Act 1 — Intro & Login (1 minute)

> "TokenMaxx classifies each prompt, enhances it, retrieves document context, routes across Groq, OpenAI, and Anthropic, streams answers live, generates files inline, and shows real-time sentiment — all while tracking savings vs. premium."

1. Sign up or log in
2. Session persists across refresh (JWT)

---

## Act 2 — Streaming + Sentiment (3 minutes)

**Prompt:** `Thanks for the help — what is photosynthesis?`

Watch:
- **Sentiment Analysis** panel (right) → likely **Positive** / Mid confidence
- Assistant reply streams token-by-token
- **Latest Routing** panel below sentiment → task, model, savings

**Prompt:** `I'm frustrated — this still isn't working!`

- Sentiment → **Frustrated**
- Chat still responds normally (sentiment does not change routing)

---

## Act 3 — Task-Aware Routing (4 minutes)

| Prompt | Expected model |
|--------|----------------|
| `Debug this React hooks error` | qwen3-32b or premium if keys set |
| `Write a Q3 business report` | Claude/GPT-4o or llama-3.3-70b |
| `URGENT: need this fixed by EOD` | Sentiment: **Urgent**; routing per task |

---

## Act 4 — Prompt Intelligence v2 (2 minutes)

Expand **View Prompt Optimization** — task, complexity, persona, strategy, enhanced prompt.

---

## Act 5 — RAG Documents (3 minutes)

1. Upload FAQ/spec in **Documents**
2. Ask a question only answerable from that file
3. Show **Document Context Used** badge in routing panel

---

## Act 6 — Document & Image Generation (3 minutes)

**Document:** `Create a one-page PDF report on renewable energy trends`

- Shows generation progress in chat
- Inline PDF attachment with preview/download

**Image:** `Generate a simple architecture diagram for a web app`

- Inline image attachment (DALL-E if OpenAI key set)

---

## Act 7 — Provider Controls (2 minutes)

1. Open **Model Controls** (admin account)
2. **Providers** section — disable **Groq** with one toggle
3. All Groq models grey out: "Disabled by provider setting"
4. Send chat message — router picks OpenAI/Anthropic (if keys set)
5. Re-enable Groq and save

---

## Act 8 — Model Regenerate (2 minutes)

Click alternate model chip → one API call, non-streaming reply.

---

## Act 9 — Activity Logs & Analytics (2 minutes)

- **Logs** tab — routing, RAG, generation events
- **Analytics** — KPIs, model/provider breakdown, CSV export

---

## Act 10 — API (optional, 1 minute)

http://127.0.0.1:8001/docs

- `POST /chat/stream` — SSE
- `POST /sentiment/analyze` — async sentiment
- `GET/PUT /provider-settings` — provider toggles
- `POST /documents/upload` — RAG
- `GET /generations/...` — download generated assets

---

## Closing

> "TokenMaxx routes eleven models across three providers with provider-level admin controls, enhances prompts intelligently, grounds answers in your documents, streams live, generates PDFs and images inline, surfaces sentiment in real time, logs every step, and proves cost savings on every request."
