# TokenMaxx — System Design

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.7.0 · **Last updated:** June 2026

---

## Problem

Teams want LLM quality without always paying premium-model prices. TokenMaxx automatically picks the best model for each task across Groq, OpenAI, and Anthropic, enhances prompts intelligently, grounds answers in uploaded documents, generates files and images on demand, surfaces message sentiment for operators, and proves savings with transparent routing metadata.

---

## Core Flows

### 1. Chat (streaming)

1. User sends message in Chat tab
2. Frontend fires `POST /sentiment/analyze` in parallel (non-blocking)
3. Frontend calls `POST /chat/stream` (SSE)
4. Backend: classify → intent → enhance → RAG → route → stream tokens (or generate file/image)
5. UI: sentiment panel updates; routing panel; token-by-token reply; inline attachments for generations

### 2. Sentiment analysis

1. On each user message, frontend calls `POST /sentiment/analyze` asynchronously
2. Panel shows label, confidence tier, explanation, conversation trend
3. Result persisted to `message_sentiments` after chat turn completes
4. **Does not** influence model routing or response content (extensible for future use)

### 3. Document / image generation

1. Intent detector routes document/image prompts away from normal chat stream
2. Document: LLM generates content → rendered to PDF/DOCX/XLSX/PPTX/MD
3. Image: DALL-E when `OPENAI_API_KEY` set; mock otherwise
4. Artifact shown inline in chat with preview and download

### 4. Provider controls

1. Admin disables provider in Model Controls → `provider_settings` table
2. All models from that provider become unavailable (`disabled_by_provider`)
3. Router excludes them via `get_enabled_model_ids()`
4. Users cannot re-enable provider-disabled models

### 5. Model regenerate

1. User clicks alternate model chip
2. `POST /chat/regenerate` — one sync LLM call
3. Non-streaming; reuses stored enhanced prompt

---

## Routing Design

| Input | Source |
|-------|--------|
| Task type | `llm_classifier` or keyword fallback |
| Complexity | `prompt_intelligence` (0–100) |
| Model scores | `model_registry` + `model_scorer` bonuses |
| Provider filter | API keys + **provider_settings** |
| Model filters | Admin disable, user disable, allowlist |

**Availability:** `provider_enabled AND admin_enabled AND user_enabled`

---

## Prompt Intelligence v2

Analyze then enhance by task, complexity, persona, and strategy. Toggle via `enhance_prompts` preference.

---

## RAG Design

Top-3 chunks above similarity threshold 0.4; per-user ChromaDB collection; injected into system prompt.

---

## Cost Model

Actual cost from LiteLLM usage × registry prices; premium baseline = GPT-4o; savings stored per `model_run`.

---

## Security

JWT auth, Fernet-encrypted user API keys, sanitized activity logs, CORS whitelist, admin role on sensitive routes.

---

## Test Coverage

| Suite | Count | Scope |
|-------|-------|-------|
| Backend pytest | 118 | Auth, chat, stream, routing, RAG, generation, sentiment, provider settings, API keys, analytics |
| Frontend Vitest | 9 | SentimentPanel UI |

```bash
cd backend && pytest -v
cd frontend && npm test
```

LLM calls mocked in CI via `ALLOW_MOCK_LLM` and test fixtures.
