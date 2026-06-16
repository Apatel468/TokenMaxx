# TokenMaxx

**Maximum Intelligence, Minimum Cost**

TokenMaxx routes prompts to the most cost-effective Groq model for each task, enhances them with Prompt Intelligence v2, streams responses live, and tracks savings versus a GPT-4o baseline.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, LiteLLM (Groq) |
| Frontend | React 18, Vite 6 |
| Auth | JWT |
| Database | SQLite |

## Features

- **LLM task classification** — Groq-powered classifier with keyword fallback
- **Prompt Intelligence Engine v2** — analyze and enhance by task type, complexity (0–100), and persona
- **SSE streaming chat** — token-by-token responses via `POST /chat/stream`
- **Task-aware routing** — complexity-aware scoring with task-specific model bonuses
- **Routing debug panel** — top 3 candidate scores, classification confidence, reason
- **Model regenerate** — retry with any top-5 model (one API call per click)
- **Model Controls** — admin org-wide and user personal toggles
- **Prompt optimization viewer** — task, complexity, persona, strategy, enhanced prompt
- **Analytics export** — `tokenmaxx-analytics-report.csv`
- **Authentication** — JWT; per-user conversations and analytics
- **Admin dashboard** — employee usage metrics
- **pytest suite** — 39 tests

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
cp .env.example .env           # add GROQ_API_KEY and JWT_SECRET
uvicorn main:app --reload --port 8001
```

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
```

## Production deployment

Backend and frontend deploy separately. After both are live, cross-link them:

1. Set `VITE_API_BASE` on Vercel to your Render API URL (e.g. `https://tokenmaxx-api.onrender.com`)
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

Required env vars: `JWT_SECRET`, `CORS_ORIGINS`. Optional: `GROQ_API_KEY` (mock mode without it), `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

For persistent data on Render, attach a disk at `/var/data` and set `DATABASE_URL=sqlite:////var/data/smartllm_router.db`.

Full guide: [docs/deploy-render.md](docs/deploy-render.md)

### Frontend — Vercel

| Setting | Value |
|---------|-------|
| Root directory | `frontend` |
| Build command | `npm run build` |
| Output directory | `dist` |

Set `VITE_API_BASE` in Vercel project settings before building — Vite embeds it at build time.

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
