# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.8.0 · **Last updated:** June 2026

---

## What TokenMaxx Is

TokenMaxx is a **cost-optimized multi-provider LLM routing platform** for teams. It classifies each prompt, enhances it with Prompt Intelligence v2, optionally retrieves context from uploaded documents (RAG) and live web pages, routes to the best allowed model across Groq, OpenAI, and Anthropic, adapts response tone from sentiment, streams the answer live, generates documents and images inline in chat, and tracks savings vs. a GPT-4o baseline.

**Stack:** FastAPI + SQLite + ChromaDB + React/Vite + LiteLLM (multi-provider) + Tavily/Serper + JWT auth.

---

## Current State (v0.8.0)

| Area | Status |
|------|--------|
| Auth | JWT login/signup; bcrypt passwords |
| Multi-provider routing | 11 chat models (Groq, OpenAI, Anthropic); provider-key filtering |
| Provider controls | Admin org-wide provider toggles (`provider_settings` table) |
| Chat | Sync `POST /chat` + **SSE** `POST /chat/stream` (default UI) |
| RAG | Document upload (TXT/MD/PDF), ChromaDB search, chat context injection |
| Web research | Tavily/Serper search, HTML scraping, direct URLs, bot-block fallback |
| Generation | Document (PDF, DOCX, XLSX, PPTX, MD) + image (DALL-E) inline in chat |
| Sentiment panel | Real-time async UI; per-message storage |
| Sentiment-aware chat | Tone guidance injected into system prompt (no routing change) |
| Prompt Intelligence v2 | Analyze + enhance; complexity 0–100 |
| Routing | LLM classifier + keyword fallback; `web_research` task type |
| Model Controls | Provider toggles + admin/user model toggles; API Keys (5 providers) |
| Activity Logs | Backend event log; **Logs** tab |
| Regenerate | One LLM call per model chip (non-streaming) |
| Analytics | KPIs + model/provider breakdown + CSV export |
| Admin | Employee usage dashboard |
| Tests | **152** pytest + **9** Vitest (SentimentPanel) |
| Deploy | Render (backend) + Vercel (frontend) |

---

## App Tabs

| Tab | Purpose |
|-----|---------|
| Chat | Streaming chat, sentiment panel, routing panel, web research badges, generation attachments |
| Analytics | Usage KPIs, model/provider breakdown, CSV export |
| Documents | Upload/manage RAG source files |
| Logs | Activity log viewer |
| Model Controls | Provider toggles, model toggles, prompt enhancement, API keys |
| Admin | Employee usage (admins only) |

---

## Key Backend Modules

| Module | Role |
|--------|------|
| `llm_classifier.py` | Groq task classification (incl. `web_research`) |
| `prompt_intelligence.py` | Analyze + enhance prompts (v2) |
| `model_scorer.py` | Complexity-aware routing; provider-key filtering |
| `model_registry.py` | Multi-provider allowlist + editorial scores |
| `model_settings.py` | Admin/user model toggles + provider toggles |
| `router_engine.py` | Score enabled models and pick best fit |
| `model_clients.py` | LiteLLM generate/stream; per-provider API key resolution |
| `chat_service.py` | Full chat pipeline |
| `web_research_service.py` | Search, scrape, fallback, inject web context |
| `web_search.py` | Tavily + Serper APIs |
| `web_scraper.py` | httpx + BeautifulSoup page fetch |
| `url_security.py` | SSRF protection, URL extraction |
| `sentiment_context.py` | Sentiment → system prompt style instructions |
| `sentiment_analyzer.py` | Rule-based sentiment classification |
| `sentiment_service.py` | Per-message sentiment persistence |
| `generation/` | Intent detection, document writer, image generator |
| `rag_service.py` | Retrieve top chunks, inject into system prompt |
| `vector_store.py` | ChromaDB persistence + similarity search |
| `activity_logger.py` | Structured event logging |
| `report_generator.py` | Analytics summary, model/provider usage |

---

## Chat Pipeline (v0.8.0)

```
classify → enhance → RAG → web research → sentiment style → route → respond/generate
```

Web research triggers on: `web_research` task type, keywords (`latest`, `pricing`, etc.), or URLs in the prompt.

---

## Model Availability

```
available = provider_enabled AND admin_enabled AND user_enabled
```

---

## API Key Resolution (chat + regenerate)

Per provider: **user key → app env key → mock**

Classifier, enhancer, title, and Groq model sync use app `.env` Groq key only.

Web search uses `TAVILY_API_KEY` or `SERPER_API_KEY` from app `.env`.

---

## Web Research

| Step | Behavior |
|------|----------|
| Direct URL | Scrape user-supplied URL (up to 5) |
| Bot block | Search Tavily/Serper for alternates; skip blocked domain |
| Scrape alternates | Fetch up to 5 pages; inject into system prompt |
| Last resort | Use search snippets if scraping fails |
| Security | SSRF blocks localhost/private IPs; timeout + size limits |

Requires `TAVILY_API_KEY` (preferred) or `SERPER_API_KEY` for search and fallback.

---

## Sentiment

| Layer | Behavior |
|-------|----------|
| Panel (UI) | Async `POST /sentiment/analyze` — parallel to chat stream |
| Pipeline | Inline rule-based analysis → tone guidance in system prompt |
| Routing | **Not** affected by sentiment |
| Labels | positive, neutral, negative, excited, frustrated, confused, urgent |

---

## Tests

```bash
cd backend && pytest -v          # 152 tests
cd frontend && npm test          # 9 Vitest tests
```

---

## Deployment

- **Backend:** Render — see [deploy-render.md](deploy-render.md)
- **Frontend:** Vercel — see [deploy-vercel.md](deploy-vercel.md)

---

## Repo

https://github.com/Apatel468/TokenMaxx
