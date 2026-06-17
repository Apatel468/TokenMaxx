# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.5.0 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M14
- [x] MVP through auth, admin, regenerate, allowlist, analytics (see prior releases)

### M15 — Quality & Polish (v0.3.3)
- [x] LLM task classifier + keyword fallback
- [x] Task-aware routing (complexity score, dynamic weights, task bonuses)
- [x] Top-3 candidate scores in routing panel
- [x] Prompt enhancement viewer (original vs enhanced)
- [x] Model settings sync (`explicitly_set`)
- [x] pytest suite + analytics CSV export

### M16 — Streaming & Prompt Intelligence (v0.4.0)
- [x] SSE streaming — `POST /chat/stream` with `routing_start`, `routing_complete`, `token`, `complete`, `error`
- [x] Real Groq streaming via LiteLLM; word-by-word fallback
- [x] Frontend live token display + typing cursor
- [x] Prompt Intelligence Engine v2 — analyze then enhance by task, complexity, persona
- [x] `PromptAnalysis` metadata in API + UI (task, complexity, persona, strategy)
- [x] Clean enhanced prompts (no internal bracket notes)
- [x] Tests: `test_chat_stream.py`, `test_prompt_intelligence.py`

### M17 — API Polish & Production Prep (v0.4.x)
- [x] `VITE_API_BASE` env for frontend
- [x] Deploy guides — Render (backend) + Vercel (frontend)
- [x] `render.yaml` blueprint
- [ ] Rename `mock_response` → `response`
- [ ] Context window truncation
- [ ] Mobile layout
- [ ] Analytics PDF export
- [ ] Streaming regenerate
- [ ] Tune registry scores from real usage
- [ ] Whisper speech-to-text UI

### M18 — RAG & Documents (v0.5.0)
- [x] ChromaDB vector store + sentence-transformers embeddings
- [x] Document upload API — TXT, MD, PDF (`POST /documents/upload`)
- [x] Document list, search, delete endpoints
- [x] RAG context injection in chat pipeline (`rag_service.py`)
- [x] RAG metadata in chat responses + SSE events
- [x] Documents tab UI (`DocumentsPage.jsx`)
- [x] Tests: `test_documents.py`, `test_chat_rag.py`

### M19 — User API Keys (v0.5.0)
- [x] Fernet encryption for stored keys (`key_encryption.py`)
- [x] CRUD + test endpoints (`/user/api-keys`)
- [x] Key resolution in chat/regenerate: user → env → mock
- [x] API Keys section in Model Controls
- [x] Tests: `test_api_keys.py`

### M20 — Activity Logs (v0.5.0)
- [x] `activity_logs` table + structured event service
- [x] Pipeline logging (classify, enhance, RAG, route, model calls)
- [x] Document and API key event logging
- [x] Logs tab UI (`LogsPage.jsx`); admin sees all users
- [x] Tests: `test_activity_logs.py`

---

## Current Milestone

**M21 — Production Hardening**

| Task | Status |
|------|--------|
| User API keys for classifier/enhancer | ⬜ |
| Persistent ChromaDB on Render disk | ⬜ |
| API key test error UX in frontend | ⬜ |
| Context window truncation | ⬜ |
| Mobile layout | ⬜ |
| Streaming regenerate | ⬜ |

---

## Future Phases

- **Phase 6** — Multi-provider (OpenAI, Anthropic, Gemini)
- **Phase 7** — Rate limits, budgets, org policies
- **Phase 8** — Docker, CI/CD, Alembic

---

## Production Readiness

**Current score:** ~85% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Task-aware complexity scoring |
| Prompt Intelligence | ✅ v2 analyze + enhance |
| Streaming chat | ✅ SSE `/chat/stream` |
| RAG | ✅ Document upload + chat context |
| Task classification | ✅ LLM + keyword fallback |
| Model regenerate | ✅ On-demand (non-streaming) |
| User API keys | ✅ Encrypted storage + resolution |
| Activity logs | ✅ Pipeline + admin viewer |
| Authentication | ✅ JWT + roles |
| Analytics export | ✅ CSV (client-side) |
| Tests | ✅ 59 pytest tests |
| Deploy | ✅ Render + Vercel guides |
