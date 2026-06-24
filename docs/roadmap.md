# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.8.0 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M21
- [x] MVP through multi-provider routing (v0.6.0)

### M22 — Sentiment, Provider Controls & Generation (v0.7.0)
- [x] Real-time sentiment analysis panel
- [x] Provider-level admin toggles
- [x] Document + image generation inline in chat
- [x] Analytics layout fixes; Vitest suite

### M23 — Web Research & Sentiment Pipeline (v0.8.0)
- [x] Web research task type + keyword/URL detection
- [x] Tavily + Serper search integration
- [x] HTML scraping with SSRF protection
- [x] Bot-protected URL → search fallback to alternate sources
- [x] Web research UI badges + source links in chat
- [x] Web metadata on `model_runs` + activity logs
- [x] Sentiment-aware response styling in chat pipeline
- [x] Tests: `test_web_research.py`, `test_sentiment_context.py`, `test_url_security.py`

---

## Current Milestone

**M24 — Production Hardening & Research Quality**

| Task | Status |
|------|--------|
| You.com / additional search providers | ⬜ |
| Headless browser for JS-heavy retail sites | ⬜ |
| Sentiment analytics dashboard | ⬜ |
| User API keys for classifier/enhancer | ⬜ |
| Persistent ChromaDB + generated files on Render disk | ⬜ |
| Context window truncation | ⬜ |
| Mobile layout | ⬜ |
| Streaming regenerate | ⬜ |
| Google Gemini chat models in catalog | ⬜ |

---

## Future Phases

- **Phase 7** — Rate limits, budgets, org policies
- **Phase 8** — Docker, CI/CD, Alembic

---

## Production Readiness

**Current score:** ~92% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Multi-provider + provider toggles |
| Prompt Intelligence | ✅ v2 analyze + enhance |
| Streaming chat | ✅ SSE `/chat/stream` |
| RAG | ✅ Document upload + chat context |
| Web research | ✅ Search + scrape + fallback (needs Tavily/Serper key) |
| Generation | ✅ Documents + images inline |
| Sentiment | ✅ Panel + pipeline tone guidance |
| Provider controls | ✅ One-click provider disable |
| User API keys | ✅ Encrypted per-provider resolution |
| Activity logs | ✅ Full pipeline visibility |
| Authentication | ✅ JWT + roles |
| Analytics | ✅ KPIs + breakdown + CSV |
| Tests | ✅ 152 pytest + 9 Vitest |
| Deploy | ✅ Render + Vercel guides |
