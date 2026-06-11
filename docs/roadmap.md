# TokenMaxx — Roadmap

> **Tagline:** Maximum Intelligence, Minimum Cost  
> **Version:** 0.3.0 · **Last updated:** June 2026

---

## Completed Milestones

### M1–M11
- [x] MVP backend, frontend, Groq/LiteLLM, analytics, multi-turn memory, docs, TokenMaxx rebrand

### M12 — Dynamic Router & Model Controls (v0.3.0)
- [x] `model_registry.py` — metadata for all Groq chat models
- [x] `groq_models.py` — Groq API catalog sync + missing-model logging
- [x] `model_scorer.py` — composite routing formula
- [x] Model Controls UI + `GET/PUT /settings/models`
- [x] SQLite `model_settings` enable/disable
- [x] Fallback when preferred model disabled
- [x] `routing_score` + `candidate_models` in chat response
- [x] Analytics layout fix (no horizontal scroll)
- [x] Docs updated to v0.3.0

---

## Current Milestone

**M13 — Quality & Polish**

| Task | Status |
|------|--------|
| Tune registry scores from real usage | ⬜ |
| Frontend: show enhancement fields in Chat UI | ⬜ |
| Context window truncation | ⬜ |
| `VITE_API_BASE` env for frontend | ⬜ |
| pytest suite (scorer, routing, settings) | ⬜ |
| LLM classifier restore (optional) | ⬜ |

---

## Next Milestone

**M14 — Streaming & API Polish**

| Task | Description |
|------|-------------|
| SSE streaming | Stream Groq tokens to frontend |
| Rename `mock_response` → `response` | API cleanup |
| Mobile layout | Collapsible sidebar + analytics |

---

## Future Phases

- **Phase 6** — Multi-provider (OpenAI, Anthropic, Gemini)
- **Phase 7** — Auth, rate limits, budgets
- **Phase 8** — Docker, CI/CD, Alembic, production deploy

---

## Production Readiness

**Current score:** ~45% production ready

| Area | Status |
|------|--------|
| Core routing | ✅ Dynamic scoring |
| Model catalog | ✅ Registry + API sync |
| User preferences | ✅ Model Controls |
| Tests | ❌ None |
| Auth | ❌ None |
| Deploy | ❌ Local only |
