# TokenMaxx — Project Memory

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.7.0 · **Last updated:** June 2026

---

## What TokenMaxx Is

TokenMaxx is a **cost-optimized multi-provider LLM routing platform** for teams. It classifies each prompt, enhances it with Prompt Intelligence v2, optionally retrieves context from uploaded documents (RAG), routes to the best allowed model across Groq, OpenAI, and Anthropic, streams the answer live, generates documents and images inline in chat, analyzes user message sentiment asynchronously, and tracks savings vs. a GPT-4o baseline.

**Stack:** FastAPI + SQLite + ChromaDB + React/Vite + LiteLLM (multi-provider) + JWT auth.

---

## Current State (v0.7.0)

| Area | Status |
|------|--------|
| Auth | JWT login/signup; bcrypt passwords |
| Multi-provider routing | 11 chat models (Groq, OpenAI, Anthropic); provider-key filtering |
| Provider controls | Admin org-wide provider toggles (`provider_settings` table) |
| Chat | Sync `POST /chat` + **SSE** `POST /chat/stream` (default UI) |
| RAG | Document upload (TXT/MD/PDF), ChromaDB search, chat context injection |
| Generation | Document (PDF, DOCX, XLSX, PPTX, MD) + image (DALL-E) inline in chat |
| Sentiment | Real-time async panel; per-message storage; does not affect routing |
| Prompt Intelligence v2 | Analyze + enhance; complexity 0–100 |
| Routing | LLM classifier + keyword fallback; task-aware scoring |
| Model Controls | Provider toggles + admin/user model toggles; API Keys (5 providers) |
| Activity Logs | Backend event log; **Logs** tab |
| Regenerate | One LLM call per model chip (non-streaming) |
| Analytics | KPIs + model/provider breakdown + CSV export |
| Admin | Employee usage dashboard |
| Tests | **118** pytest + **9** Vitest (SentimentPanel) |
| Deploy | Render (backend) + Vercel (frontend) |

---

## App Tabs

| Tab | Purpose |
|-----|---------|
| Chat | Streaming chat, sentiment panel, routing panel, generation attachments |
| Analytics | Usage KPIs, model/provider breakdown, CSV export |
| Documents | Upload/manage RAG source files |
| Logs | Activity log viewer |
| Model Controls | Provider toggles, model toggles, prompt enhancement, API keys |
| Admin | Employee usage (admins only) |

---

## Key Backend Modules

| Module | Role |
|--------|------|
| `llm_classifier.py` | Groq task classification |
| `prompt_intelligence.py` | Analyze + enhance prompts (v2) |
| `model_scorer.py` | Complexity-aware routing; provider-key filtering |
| `model_registry.py` | Multi-provider allowlist + editorial scores |
| `model_settings.py` | Admin/user model toggles + provider toggles |
| `groq_models.py` | Model catalog sync |
| `router_engine.py` | Score enabled models and pick best fit |
| `model_clients.py` | LiteLLM generate/stream; per-provider API key resolution |
| `chat_service.py` | Full chat pipeline (classify → enhance → RAG → route → respond) |
| `generation/` | Intent detection, document writer, image generator |
| `generation_service.py` | Orchestration + persistence for generated assets |
| `sentiment_analyzer.py` | Rule-based sentiment classification |
| `sentiment_service.py` | Per-message sentiment persistence |
| `rag_service.py` | Retrieve top chunks, inject into system prompt |
| `vector_store.py` | ChromaDB persistence + similarity search |
| `document_processor.py` | Chunk TXT/MD/PDF for embedding |
| `api_key_service.py` | Encrypted per-user provider keys |
| `activity_logger.py` | Structured event logging |
| `report_generator.py` | Analytics summary, model/provider usage |

---

## Model Availability

```
available = provider_enabled AND admin_enabled AND user_enabled
```

Provider toggles: `GET/PUT /provider-settings` (PUT admin only).

---

## API Key Resolution (chat + regenerate)

Per provider:

1. User's stored key for that provider (if set and active)
2. App-level env key (`GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`)
3. Mock response if `ALLOW_MOCK_LLM=true` (default locally)

Classifier, enhancer, title, and Groq model sync use app `.env` keys only (Groq).

---

## Sentiment Analysis

- Runs **asynchronously** via `POST /sentiment/analyze` (parallel to chat stream)
- Does **not** block or alter chat routing or responses
- Labels: positive, neutral, negative, excited, frustrated, confused, urgent
- Stored in `message_sentiments`; shown in right-side **Sentiment Analysis** panel
- Designed for future emotion/toxicity/mood analytics

---

## Generation Pipeline

1. `detect_generation_intent()` classifies prompt as chat, document, or image
2. Document: LLM writes content → ReportLab/python-docx/etc. render file
3. Image: DALL-E (OpenAI key) or mock placeholder
4. Artifact attached inline to assistant message in chat (preview + download)

---

## Tests

```bash
cd backend && pytest -v          # 118 tests
cd frontend && npm test          # 9 Vitest tests
```

---

## Deployment

- **Backend:** Render — see [deploy-render.md](deploy-render.md)
- **Frontend:** Vercel — see [deploy-vercel.md](deploy-vercel.md)
- Cross-link: `VITE_API_BASE` ↔ `CORS_ORIGINS`

---

## Repo

https://github.com/Apatel468/TokenMaxx
