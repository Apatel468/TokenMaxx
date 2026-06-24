# TokenMaxx — Architectural Decisions

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.8.0 · **Last updated:** June 2026  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Backend | FastAPI | OpenAPI, Pydantic, `StreamingResponse` for SSE |
| Database | SQLite | Zero setup for MVP |
| Vector store | ChromaDB + sentence-transformers | Local persistence; no external vector DB for MVP |
| Web search | Tavily (preferred) + Serper fallback | Structured results with snippets for fallback |
| Web scraping | httpx + BeautifulSoup | Python-native; static HTML extraction |
| Auth | bcrypt + PyJWT (HS256) | Simple stateless tokens |
| LLM gateway | LiteLLM | Unified multi-provider interface + `stream=True` |
| Streaming | Server-Sent Events | `POST /chat/stream`; frontend uses fetch + ReadableStream |
| Providers | Groq, OpenAI, Anthropic (allowlisted) | Cost/speed on Groq; premium tiers when keys configured |
| Frontend | React + Vite | Fast iteration |
| Tests | pytest + Vitest | 152 backend + 9 frontend tests; mocked LLM/search in CI |

---

## Architectural Decisions

### Multi-provider model allowlist (v0.6.0) 🔒
11 chat models across Groq (6), OpenAI (3), Anthropic (2). Routing filtered to providers with API keys.

### SSE streaming chat (v0.4.0) 🔒
`POST /chat/stream` with `routing_complete` before tokens. Persistence after stream completes.

### Prompt Intelligence Engine v2 (v0.4.0) 🔒
`prompt_intelligence.py` — analyze then enhance with complexity tiers and personas.

### RAG with ChromaDB (v0.5.0) 🔒
Per-user collections; top-3 chunks; threshold 0.4; injected into system prompt after enhancement.

### User API keys (v0.5.0) 🔒
Fernet-encrypted per-provider keys. Resolution: user → env → mock.

### Provider-level controls (v0.7.0) 🔒
`available = provider_enabled AND admin_enabled AND user_enabled`

### Real-time sentiment panel (v0.7.0)
Async `POST /sentiment/analyze` for UI panel + `message_sentiments` persistence.

### Sentiment-aware response styling (v0.8.0)
**Decision:** Inline rule-based sentiment in `prepare_chat_turn()` appends tone guidance to `system_prompt`.  
**Does not affect:** Model routing or task classification.  
**Mapping:** frustrated/negative → empathetic concise; confused → step-by-step; urgent → actionable steps.  
**Why:** Improve UX without blocking streaming or adding LLM latency.

### Web research & scraping (v0.8.0) 🔒
**Decision:** Optional pipeline step after RAG, before routing in `chat_service.prepare_chat_turn()`.  
**Search:** Tavily preferred, Serper fallback (`web_search.py`).  
**Scrape:** httpx + BeautifulSoup (`web_scraper.py`); SSRF protection (`url_security.py`).  
**Triggers:** `web_research` task type, keywords (`latest`, `pricing`, etc.), or URLs in prompt.  
**Direct URLs:** Scrape up to 5; skip search API.  
**Bot-protected fallback:** On scrape failure, search alternate sources (exclude blocked domain); last resort = search snippets only.  
**Requires:** `TAVILY_API_KEY` or `SERPER_API_KEY` for search/fallback (direct scrape of friendly sites works without search key).  
**Storage:** Web metadata on `model_runs`; sources in API response and conversation history.  
**Why:** Answer questions requiring fresh web data without a separate research UI.

### Document & image generation (v0.7.0) 🔒
Intent detection branches to document/image flows; inline chat attachments.

### Original prompt preserved in DB 🔒
User `messages.content` = original text; `model_runs.enhanced_prompt` = enhanced text sent to model.

---

## LLM Touchpoints (with API key)

| Step | When | Model / service | Key source |
|------|------|-----------------|------------|
| Classify | Each chat turn | llama-3.1-8b-instant | App `GROQ_API_KEY` |
| Analyze + enhance | Each turn (if enabled) | Prompt Intelligence v2 | App `GROQ_API_KEY` |
| RAG embed/search | Upload + each turn | sentence-transformers + ChromaDB | N/A |
| Web search | When web research triggers | Tavily / Serper API | `TAVILY_API_KEY` / `SERPER_API_KEY` |
| Web scrape | When web research triggers | httpx (no LLM) | N/A |
| Sentiment (pipeline) | Each chat turn | Rule-based (no LLM) | N/A |
| Route + respond | Each chat turn | Scored allowlisted model | User key → env → mock |
| Title | First turn | auxiliary.title | App `GROQ_API_KEY` |

---

## Registry Score Caveat

Scores in `model_registry.py` are editorial estimates. Routing uses `model_scorer.py` bonuses; enhancement uses `prompt_intelligence.py` personas.
