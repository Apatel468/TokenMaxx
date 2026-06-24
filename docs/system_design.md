# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.8.0 · **Last updated:** June 2026

---

## Problem

Teams want LLM quality without always paying premium-model prices. TokenMaxx automatically picks the best model for each task across Groq, OpenAI, and Anthropic, enhances prompts intelligently, grounds answers in uploaded documents and live web content, adapts tone to user sentiment, generates files and images on demand, and proves savings with transparent routing metadata.

---

## Core Flows

### 1. Chat (streaming)

1. User sends message in Chat tab
2. Frontend fires `POST /sentiment/analyze` in parallel (panel only)
3. Frontend calls `POST /chat/stream` (SSE)
4. Backend: classify → intent → enhance → RAG → **web research** → **sentiment style** → route → stream
5. UI: sentiment panel, routing panel (with web research badges), token-by-token reply

### 2. Web research

1. Triggered when task is `web_research`, prompt has research keywords, or contains URLs
2. **Direct URL:** scrape up to 5 URLs (SSRF-protected)
3. **Bot-protected URL:** if scrape fails and `TAVILY_API_KEY`/`SERPER_API_KEY` set → search for alternates
4. Scrape alternates or fall back to search snippets
5. Content injected into `system_prompt`; model instructed to cite sources
6. UI shows 🌐 Web Research badge + source links; activity log records `web_research_completed`

### 3. Sentiment

| Layer | Behavior |
|-------|----------|
| **Panel** | Async API for UI; does not block chat |
| **Pipeline** | Inline rule-based analysis → `## User tone guidance` in system prompt |
| **Routing** | Unchanged |

Frustrated/urgent → concise empathetic replies. Confused → step-by-step. Neutral/positive → no extra instruction.

### 4. RAG

Top-3 chunks above similarity threshold 0.4; per-user ChromaDB collection; injected into system prompt.

### 5. Document / image generation

Intent detector branches to document or image flows; artifacts inline in chat.

### 6. Provider controls

Admin disables provider → all models from that provider excluded from routing.

---

## Routing Design

| Input | Source |
|-------|--------|
| Task type | `llm_classifier` or keyword fallback (12 types incl. `web_research`) |
| Complexity | `model_scorer.compute_complexity()` |
| Model scores | `model_registry` + `model_scorer` bonuses |
| Provider filter | API keys + `provider_settings` |
| Model filters | Admin disable, user disable, allowlist |

**Availability:** `provider_enabled AND admin_enabled AND user_enabled`

**Web research task** prefers: `openai/gpt-oss-120b`, `llama-3.3-70b-versatile`, `qwen/qwen3-32b` (via `TASK_MODEL_BONUSES`).

---

## Prompt Intelligence v2

Analyze then enhance by task, complexity, persona, and strategy. Toggle via `enhance_prompts` preference.

---

## Cost Model

Actual cost from LiteLLM usage × registry prices; premium baseline = GPT-4o; savings stored per `model_run`.

---

## Security

| Area | Measure |
|------|---------|
| Auth | JWT, bcrypt |
| User API keys | Fernet encryption |
| Web scraping | SSRF blocks localhost/private IPs; timeout + max page size |
| Activity logs | Sanitized metadata (no raw keys/prompts) |
| CORS | Whitelist in production |

---

## Test Coverage

| Suite | Count | Scope |
|-------|-------|-------|
| Backend pytest | 152 | Auth, chat, stream, routing, RAG, web research, sentiment, generation, provider settings |
| Frontend Vitest | 9 | SentimentPanel UI |

```bash
cd backend && pytest -v
cd frontend && npm test
```

LLM and external APIs mocked in tests via fixtures and monkeypatch.
