# TokenMaxx — Demo Script

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.8.0

Use this script to demo TokenMaxx to stakeholders in 30–40 minutes.

---

## Setup (before the demo)

1. Start backend: `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Set API keys in `backend/.env`:
   - `GROQ_API_KEY` — classifier, enhancer, Groq models, document content
   - `TAVILY_API_KEY` — web research (keys start with `tvly-`; get at app.tavily.com)
   - `OPENAI_API_KEY` — optional; GPT-4o routing + DALL-E images
   - `ANTHROPIC_API_KEY` — optional; Claude routing
5. Set `JWT_SECRET`
6. **Restart backend** after any `.env` change
7. (Optional) Upload a sample file in **Documents** for RAG demo

---

## Act 1 — Intro & Login (1 minute)

> "TokenMaxx classifies each prompt, enhances it, retrieves document and web context, routes across three providers, adapts tone from sentiment, streams answers live, and tracks savings vs. premium."

1. Sign up or log in
2. Session persists across refresh (JWT)

---

## Act 2 — Streaming + Sentiment (3 minutes)

**Prompt:** `Thanks for the help — what is photosynthesis?`

Watch:
- **Sentiment Analysis** panel → likely **Positive**
- Assistant streams token-by-token
- **Latest Routing** panel → task, model, savings

**Prompt:** `I'm frustrated — this still isn't working!`

- Sentiment panel → **Frustrated**
- Routing panel may show **Sentiment-aware response**
- Reply should be more direct/empathetic (tone guidance in system prompt)

---

## Act 3 — Web Research (5 minutes)

### Friendly URL (direct scrape)

**Prompt:**
```
Summarize https://en.wikipedia.org/wiki/2026_24_Hours_of_Le_Mans
```

Watch:
- **🌐 Web Research** badge
- Clickable source link
- Summary grounded in page content

Check **Logs** → `web_research_completed` with `web_research_used: true`

### Search-based research

**Prompt:** `What is OpenAI's latest API pricing?`

- Task type may be `web_research`
- Sources from Tavily search + scrape

### Bot-protected URL (fallback)

**Prompt:**
```
Describe this product and give me the price:
https://www.sephora.com/product/pretty-grunge-eyeshadow-palette-P507079
```

Watch:
- **Alternate sources (original link blocked)** badge
- `web_fallback_used: true` in activity log
- Answer cites alternate retailers/review sites (not Sephora directly)

> Requires valid `TAVILY_API_KEY` and backend restart after adding it.

---

## Act 4 — Task-Aware Routing (3 minutes)

| Prompt | Expected behavior |
|--------|-------------------|
| `Debug this React hooks error` | Coding task; qwen3-32b or premium |
| `Write a Q3 business report` | Business/report; Claude/GPT-4o bias |
| `URGENT: need this fixed by EOD` | Urgent sentiment + concise routing |

---

## Act 5 — Prompt Intelligence v2 (2 minutes)

Expand **View Prompt Optimization** — task, complexity, persona, strategy, enhanced prompt.

---

## Act 6 — RAG Documents (3 minutes)

1. Upload FAQ/spec in **Documents**
2. Ask a question only answerable from that file
3. Show **Document Context Used** badge

---

## Act 7 — Document & Image Generation (3 minutes)

**Document:** `Create a one-page PDF report on renewable energy trends`

**Image:** `Generate a simple architecture diagram for a web app`

---

## Act 8 — Provider Controls (2 minutes)

1. **Model Controls** → disable **Groq**
2. Send chat → router picks OpenAI/Anthropic
3. Re-enable Groq

---

## Act 9 — Logs & Analytics (2 minutes)

- **Logs** — `web_research_started/completed`, routing, RAG events
- **Analytics** — KPIs, model/provider breakdown, CSV export

---

## Act 10 — API (optional, 1 minute)

http://127.0.0.1:8001/docs

- `POST /chat/stream` — SSE with web research metadata
- `POST /sentiment/analyze`
- `POST /documents/upload`

---

## Closing

> "TokenMaxx routes eleven models across three providers, enhances prompts, grounds answers in your documents and live web sources, adapts tone from sentiment, streams live, generates files inline, logs every step, and proves cost savings on every request."

---

## Troubleshooting during demo

| Issue | Fix |
|-------|-----|
| Web research fails on Sephora | Expected without Tavily key; add `TAVILY_API_KEY` and restart |
| `Unable to retrieve web search results` | Wrong API key format (must be `tvly-`, not You.com `ydc-sk-`) |
| No web research badge | Check Logs for `web_research_used`; restart backend after `.env` change |
| Wikipedia works, Sephora doesn't | Bot protection — fallback needs Tavily |
