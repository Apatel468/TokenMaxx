# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.7.0 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M21
- [x] MVP through multi-provider routing (v0.6.0) — see prior releases in git history

### M22 — Sentiment, Provider Controls & Generation (v0.7.0)
- [x] Real-time sentiment analysis panel (async, non-blocking)
- [x] `message_sentiments` table + `POST /sentiment/analyze` API
- [x] Provider-level admin toggles (`provider_settings` table)
- [x] `GET/PUT /provider-settings`; availability = provider ∧ admin ∧ user
- [x] Model Controls UI grouped by provider with model counts
- [x] Document generation (PDF, DOCX, XLSX, PPTX, MD) inline in chat
- [x] Image generation (DALL-E / mock) inline in chat
- [x] Generation intent detection + `generations` router (download, preview, history)
- [x] Analytics model usage table layout fixes
- [x] Frontend Vitest suite (SentimentPanel)
- [x] Tests: `test_sentiment.py`, `test_provider_settings.py`, `test_generation_*.py`

---

## Current Milestone

**M23 — Production Hardening & Sentiment Integration**

| Task | Status |
|------|--------|
| Wire sentiment into routing / prompt tone (optional) | ⬜ |
| Sentiment analytics dashboard | ⬜ |
| User API keys for classifier/enhancer | ⬜ |
| Persistent ChromaDB + generated files on Render disk | ⬜ |
| Context window truncation | ⬜ |
| Mobile layout | ⬜ |
| Streaming regenerate | ⬜ |
| Google Gemini chat models in catalog | ⬜ |
| Emotion / toxicity scoring | ⬜ |

---

## Future Phases

- **Phase 7** — Rate limits, budgets, org policies
- **Phase 8** — Docker, CI/CD, Alembic

---

## Production Readiness

**Current score:** ~90% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Multi-provider + provider toggles |
| Prompt Intelligence | ✅ v2 analyze + enhance |
| Streaming chat | ✅ SSE `/chat/stream` |
| RAG | ✅ Document upload + chat context |
| Generation | ✅ Documents + images inline in chat |
| Sentiment | ✅ Real-time panel + persistence (display-only) |
| Provider controls | ✅ One-click provider disable |
| User API keys | ✅ Encrypted per-provider resolution |
| Activity logs | ✅ Pipeline + admin viewer |
| Authentication | ✅ JWT + roles |
| Analytics | ✅ KPIs + model/provider breakdown + CSV |
| Tests | ✅ 118 pytest + 9 Vitest |
| Deploy | ✅ Render + Vercel guides |
