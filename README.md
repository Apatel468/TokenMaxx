# TokenMaxx

**Maximum Intelligence, Minimum Cost**

TokenMaxx routes prompts to the most cost-effective LLM for each task across Groq, OpenAI, and Anthropic, enhances them with Prompt Intelligence v2, retrieves context from uploaded documents (RAG), streams responses live, generates documents and images inline in chat, analyzes message sentiment in real time, and tracks savings versus a GPT-4o baseline.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy, LiteLLM (multi-provider) |
| Frontend | React 18, Vite 6, Vitest |
| Auth | JWT |
| App database | SQLite (users, conversations, analytics, document metadata, sentiment, generations) |
| Vector store | ChromaDB + sentence-transformers (RAG chunk embeddings) |

## Features

- **Multi-provider routing** — 11 curated chat models across Groq, OpenAI, and Anthropic; routes only to providers with configured API keys
- **Provider-level controls** — admins disable entire providers (Groq, OpenAI, Anthropic) in one toggle; cascades to all models
- **LLM task classification** — Groq-powered classifier with keyword fallback
- **Prompt Intelligence v2** — analyze and enhance by task type, complexity (0–100), and persona
- **RAG document context** — upload TXT/MD/PDF; chat retrieves relevant chunks from ChromaDB
- **Document & image generation** — detect intent in chat; generate PDF, DOCX, XLSX, PPTX, Markdown, and images inline as attachments
- **Real-time sentiment analysis** — async tone classification panel (positive, neutral, frustrated, urgent, etc.); stored per message
- **SSE streaming chat** — token-by-token responses via `POST /chat/stream`
- **Task-aware routing** — complexity-aware scoring with task-specific model bonuses
- **Routing debug panel** — top candidates, provider availability, classification confidence
- **Model regenerate** — retry with any top-5 model (one API call per click)
- **Model Controls** — provider toggles + per-model admin/user toggles; per-user API keys
- **Documents** — upload, list, and delete RAG source files
- **Activity logs** — timestamped backend events for routing, RAG, model calls, and errors
- **Analytics** — usage KPIs, model and provider breakdown, CSV export
- **Authentication** — JWT; per-user conversations and analytics
- **Admin dashboard** — employee usage metrics
- **Tests** — 118 backend pytest tests + 9 frontend Vitest tests

## Supported models (chat)

| Provider | Models |
|----------|--------|
| Groq | llama-3.1-8b-instant, llama-3.3-70b-versatile, llama-4-scout-17b, qwen3-32b, gpt-oss-20b, gpt-oss-120b |
| OpenAI | gpt-4o-mini, gpt-4o, o3-mini |
| Anthropic | claude-3-5-sonnet, claude-3-haiku |

Groq-hosted models are optionally synced against the live Groq API when `GROQ_API_KEY` is set. `whisper-large-v3` is cataloged for audio but is not chat-routable.

**Model availability:** `provider_enabled AND admin_enabled AND user_enabled`

## App tabs

| Tab | Purpose |
|-----|---------|
| Chat | Streaming chat, sentiment panel, routing panel, inline generation attachments |
| Analytics | Usage KPIs, model/provider breakdown, CSV export |
| Documents | Upload/manage RAG files (TXT, MD, PDF) |
| Logs | Activity log viewer (admin can see all users) |
| Model Controls | Provider toggles, model toggles, prompt enhancement, API keys |
| Admin | Employee usage (admins only) |

## Local development

### Prerequisites

- Python 3.12+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env           # add API keys and JWT_SECRET
uvicorn main:app --reload --port 8001
```

First RAG upload downloads the `all-MiniLM-L6-v2` embedding model (~90 MB).

At minimum set `GROQ_API_KEY` for classifier/enhancer/title and document generation content. Add `OPENAI_API_KEY` for OpenAI routing and real image generation (DALL-E).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local     # VITE_API_BASE defaults to http://127.0.0.1:8001
npm run dev
```

### Local URLs

| Service | URL |
|---------|-----|
| App | http://localhost:5173 |
| API docs | http://127.0.0.1:8001/docs |
| Health | http://127.0.0.1:8001/health |

### Tests

```bash
cd backend && source venv/bin/activate && pytest -v
cd frontend && npm test
```

## Environment variables (backend)

See `backend/.env.example`. Key vars:

| Variable | Purpose |
|----------|--------|
| `GROQ_API_KEY` | Groq inference + classifier/enhancer/title/document content |
| `OPENAI_API_KEY` | OpenAI routing + DALL-E image generation |
| `ANTHROPIC_API_KEY` | App-level Anthropic key (enables Claude models) |
| `GEMINI_API_KEY` | App-level Google key (for user key testing; no Gemini chat models yet) |
| `JWT_SECRET` | Auth token signing |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path (default: `backend/chroma_data/`) |
| `GENERATED_FILES_DIR` | Generated documents/images storage (default: `backend/generated_data/`) |
| `RAG_SIMILARITY_THRESHOLD` | Min score for RAG chunks in chat (default: `0.4`) |
| `API_KEY_ENCRYPTION_SECRET` | Encrypt user API keys at rest (falls back to `JWT_SECRET`) |
| `ALLOW_MOCK_LLM` | Mock responses when no key (default: `true` for local demos) |
| `CORS_ORIGINS` | Comma-separated frontend URLs (production) |

API key resolution for chat/regenerate: **user key → app env key → mock** (per provider).

## Production deployment

Backend and frontend deploy separately. After both are live, cross-link them:

1. Set `VITE_API_BASE` on Vercel to your Render API URL
2. Set `CORS_ORIGINS` on Render to your Vercel frontend URL
3. Redeploy both services

### Backend — Render

Use the blueprint at [`render.yaml`](render.yaml) or configure manually.

| Setting | Value |
|---------|-------|
| Root directory | `backend` |
| Build command | `pip install --upgrade pip && pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |

Required: `JWT_SECRET`, `CORS_ORIGINS`. Recommended: `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `API_KEY_ENCRYPTION_SECRET`.

For persistent SQLite, attach a disk at `/var/data`. For persistent RAG vectors and generated files, set `CHROMA_PERSIST_DIR` and `GENERATED_FILES_DIR` on mounted disk paths.

Full guide: [docs/deploy-render.md](docs/deploy-render.md)

### Frontend — Vercel

| Setting | Value |
|---------|-------|
| Root directory | `frontend` |
| Build command | `npm run build` |
| Output directory | `dist` |

Set `VITE_API_BASE` before building — Vite embeds it at build time.

Full guide: [docs/deploy-vercel.md](docs/deploy-vercel.md)

## Repository

https://github.com/Apatel468/TokenMaxx

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/project_memory.md](docs/project_memory.md) | Project overview |
| [docs/architecture.md](docs/architecture.md) | Technical architecture |
| [docs/system_design.md](docs/system_design.md) | System design summary |
| [docs/demo_script.md](docs/demo_script.md) | Demo walkthrough |
| [docs/roadmap.md](docs/roadmap.md) | Milestones |
| [docs/decisions.md](docs/decisions.md) | Architectural decisions |
| [docs/deploy-render.md](docs/deploy-render.md) | Render backend deployment |
| [docs/deploy-vercel.md](docs/deploy-vercel.md) | Vercel frontend deployment |
