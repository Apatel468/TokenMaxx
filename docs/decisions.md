# SmartLLM Router — Architectural Decisions

> Record of major decisions, tradeoffs, and rules for future developers.  
> **Do not change items marked 🔒 without team review.**

---

## Technology Choices

### FastAPI (Backend framework)
**Decision:** Use FastAPI over Flask/Django.  
**Why:** Auto OpenAPI docs, Pydantic validation, async-ready, beginner-friendly.  
**Tradeoff:** Less built-in admin/ORM than Django; acceptable for MVP.

### SQLite (Database)
**Decision:** SQLite for MVP persistence.  
**Why:** Zero setup, single file, perfect for demos and local dev.  
**Tradeoff:** No concurrent writes at scale; migrate to PostgreSQL before production.  
**🔒 Do not** switch to Postgres without adding migrations and updating deployment docs.

### LiteLLM (LLM gateway)
**Decision:** Use LiteLLM instead of direct Groq SDK calls.  
**Why:** Unified API surface; easy to add providers later with one-line model string changes.  
**Tradeoff:** Extra dependency layer; debugging can be opaque.

### Groq-only provider (Phase 2 pivot)
**Decision:** Remove active OpenAI/Anthropic/Gemini paths; only Groq is wired.  
**Why:** Simplify MVP, one API key, fast inference, low cost for demos.  
**Tradeoff:** Less impressive "multi-provider router" story until Phase 5.  
**Note:** Early code comments may still mention other providers historically.

### React + Vite (Frontend)
**Decision:** React 18 with Vite, no Next.js, no UI component library.  
**Why:** User requested beginner-friendly stack; minimal magic; fast dev server.  
**Tradeoff:** More manual CSS; no SSR/SEO (fine for internal demo).

### Plain CSS (No Tailwind/MUI)
**Decision:** Custom CSS variables in `index.css` + `App.css`.  
**Why:** Fewer dependencies; easier for beginners to read.  
**Tradeoff:** Slower to build complex UIs.

### YAML config (`config/models.yaml`)
**Decision:** Externalize routing, pricing, and premium baseline to YAML.  
**Why:** Change models without code deploy; non-developers can edit routes.  
**Tradeoff:** Config cached in memory at startup — **requires server restart** after YAML edits.  
**🔒 Do not** hard-code model routing in Python without strong justification.

---

## Architectural Decisions

### Service layer between routers and persistence
**Decision:** Business logic lives in `backend/services/`, not in routers.  
**Why:** Testability, separation of concerns, beginner-readable modules.  
**🔒 Keep routers thin** — orchestration only.

### Keyword classifier (not ML)
**Decision:** Regex keyword matching for task classification.  
**Why:** Zero latency, zero cost, no extra API call, easy to understand.  
**Tradeoff:** Brittle; misroutes ambiguous or multi-intent prompts.  
**Future:** Replace with small LLM classifier (see roadmap Phase 4).

### GPT-4o as savings baseline (not Groq premium)
**Decision:** Compare all costs against GPT-4o rates from YAML, not best Groq model.  
**Why:** Clear narrative: "You saved X% vs always using premium OpenAI."  
**Tradeoff:** Savings % is illustrative, not a literal invoice comparison.

### Mock fallback always available
**Decision:** Missing `GROQ_API_KEY` or Groq API errors → mock response, never 500.  
**Why:** Demo works offline; resilient MVP.  
**Tradeoff:** User may not realize they got a mock unless they read response prefix.

### Three-table conversation schema
**Decision:** `conversations` + `messages` + `model_runs` (not one flat table).  
**Why:** Multi-turn memory, per-turn routing metrics, clean analytics aggregation.  
**Tradeoff:** More joins; analytics code must handle multiple model_runs per conversation.

### Per-turn re-routing in conversations
**Decision:** Each new message in a thread re-classifies task type and may pick a different model.  
**Why:** Latest message intent may differ from thread start (e.g. started with coding, then asks Q&A).  
**Tradeoff:** Inconsistent model within thread; may confuse users.  
**Future consideration:** Lock model per conversation or re-route only on explicit task change.

### Full history sent to Groq every turn
**Decision:** No truncation; entire `message_history` passed to LiteLLM.  
**Why:** Simplest correct multi-turn behavior for MVP.  
**Tradeoff:** Token limits, cost growth, latency on long threads.  
**🔒 Add truncation before production** — see roadmap M8.

### `conversation_id` optional on POST /chat
**Decision:** Omit id → new conversation; include id → append to thread.  
**Why:** RESTful simplicity; no separate "create conversation" endpoint needed.

### Analytics aggregates from `model_runs` (not legacy `chat_history`)
**Decision:** Phase 3 analytics read `model_runs` table exclusively.  
**Why:** Richer per-turn data (tokens, latency, mock flag).  
**Known gap:** `/analytics/history` conversation view only surfaces first exchange — **bug to fix**.

---

## Assumptions

1. **Single user / no auth** — Anyone with API access can read all conversations.
2. **Local development only** — Ports 8001 (backend) and 5173 (frontend).
3. **English prompts** — Keyword rules tuned for English.
4. **USD pricing** — All cost numbers illustrative from public rate cards.
5. **One Groq API key** — Shared across all requests; no per-user keys.
6. **Trust client for conversation_id** — No ownership check on threads.
7. **~4 chars per token** — Used when LiteLLM doesn't return usage (mocks).

---

## Important Implementation Notes

### Environment variables
- Only `GROQ_API_KEY` is used in active code path.
- Loaded via `python-dotenv` in `main.py` and `model_clients.py`.
- **🔒 NEVER read, log, display, or commit `.env` file contents** (explicit project rule).

### LiteLLM model string format
```
YAML model: llama-3.3-70b-versatile  →  litellm: groq/llama-3.3-70b-versatile
YAML model: qwen/qwen3-32b           →  litellm: groq/qwen/qwen3-32b
```
See `model_clients._to_litellm_model()`.

### Config cache
`config_loader._config_cache` is populated once. Restart uvicorn after editing `models.yaml`.

### Database file location
`sqlite:///./smartllm_router.db` — relative to **current working directory** when uvicorn starts. Always run from `backend/` directory.

### CORS origins
Hardcoded: `http://localhost:5173`, `http://127.0.0.1:5173`. Update if frontend port changes.

### Response field naming debt
`ChatResponse.mock_response` contains real Groq text too — legacy name from Phase 1. Renaming is a breaking API change; plan for v0.2.

### Pydantic v2 Config
Some models use `class Config: from_attributes = True` (Pydantic v1 style). Still works in Pydantic v2.

### Windows development
Project developed on Windows; paths use backslashes in docs but code uses `pathlib` for portability. Port 8000 frequently conflicts — **standard port is 8001**.

---

## Things NOT to Change Without Review 🔒

| Item | Reason |
|------|--------|
| `config/models.yaml` structure | Breaks config_loader, cost_tracker, models router |
| `model_runs` schema | Breaks analytics aggregations |
| Mock fallback behavior | Demo reliability depends on it |
| GPT-4o premium baseline semantics | Product story and savings % meaning |
| `.env` gitignore | Security |
| Service layer pattern | Testability and readability |
| Groq-only in model_clients (unless Phase 5) | Scope control |

---

## Rejected Alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Hard-coded routing in Python | Changed to YAML in Phase 2 |
| One new conversation per `/chat` always | Changed in Phase 3A for memory |
| OpenAI/Anthropic/Gemini active paths | Groq-only pivot for simplicity |
| React Router | Overkill for two tabs |
| Tailwind CSS | User wanted beginner-friendly plain CSS |
| Separate classifier LLM call | Cost + latency for MVP |
| PostgreSQL from day one | SQLite sufficient for MVP |

---

## Decision Log (Chronological)

| Date (approx) | Decision |
|---------------|----------|
| Phase 1 | Mock-first MVP, keyword routing |
| Phase 2 | LiteLLM integration, multi-provider then Groq-only |
| Phase 2 | YAML externalized routing |
| Phase 3 | Three-table SQLite schema |
| Phase 3 | Analytics endpoints + dashboard |
| Phase 3A | Multi-turn conversation_id + full history to model |
| Phase 3A | GET /conversations endpoints |
| Docs | Permanent memory in docs/ folder |

---

## Questions for Future Review

1. Should routing lock to first message's model within a conversation?
2. Should `total_chats` in analytics count conversations or model_runs (turns)?
3. Should we expose per-turn analytics in `/analytics/history`?
4. When to rename `mock_response` → `response`?
5. Is GPT-4o still the right savings baseline as Groq adds premium models?

Document answers here when decided.
