# Deploy TokenMaxx Backend to Render

This guide covers the FastAPI backend in `backend/`. The React frontend is deployed separately (e.g. Render Static Site, Vercel, Netlify) with `VITE_API_BASE` pointing at this API.

---

## Render commands (exact)

| Step | Command |
|------|---------|
| **Root directory** | `backend` |
| **Build command** | `pip install --upgrade pip && pip install -r requirements.txt` |
| **Start command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Health check path** | `/health` |

Render sets `$PORT` automatically — do not hardcode `8001` in production.

---

## Option A — Blueprint (`render.yaml`)

1. Push this repo to GitHub.
2. In [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**.
3. Connect the repo; Render reads `render.yaml` at the repo root.
4. Set secret env vars when prompted:
   - `GROQ_API_KEY`
   - `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (optional; enables multi-provider routing)
   - `CORS_ORIGINS` (your deployed frontend URL)
   - `API_KEY_ENCRYPTION_SECRET` (recommended for user API keys)
   - Optional: `ADMIN_EMAIL`, `ADMIN_PASSWORD`
   - Optional: `CHROMA_PERSIST_DIR=/var/data/chroma` (with persistent disk)
5. Deploy.

The blueprint provisions:
- Web service `tokenmaxx-api`
- 1 GB persistent disk at `/var/data`
- `DATABASE_URL=sqlite:////var/data/smartllm_router.db`
- Auto-generated `JWT_SECRET`

---

## Option B — Manual Web Service

1. **New** → **Web Service** → connect GitHub repo.
2. Configure:

| Setting | Value |
|---------|-------|
| Name | `tokenmaxx-api` |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install --upgrade pip && pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

3. **Environment** variables:

| Key | Required | Notes |
|-----|----------|-------|
| `JWT_SECRET` | Yes | Long random string; Render can generate |
| `GROQ_API_KEY` | No | Groq inference + classifier/enhancer; without it, LLM responses are mocked |
| `OPENAI_API_KEY` | No | Enables OpenAI model routing (gpt-4o-mini, gpt-4o, o3-mini) |
| `ANTHROPIC_API_KEY` | No | Enables Anthropic model routing (Claude) |
| `GEMINI_API_KEY` | No | For Google user key testing (no Gemini chat models in catalog yet) |
| `DATABASE_URL` | No | Default local path; use disk path on Render (below) |
| `CORS_ORIGINS` | Yes (prod) | e.g. `https://your-frontend.onrender.com` |
| `JWT_EXPIRE_HOURS` | No | Default `168` |
| `ADMIN_EMAIL` | No | Seeds admin on startup |
| `ADMIN_PASSWORD` | No | Seeds admin on startup |
| `API_KEY_ENCRYPTION_SECRET` | Recommended | Encrypts user API keys at rest |
| `CHROMA_PERSIST_DIR` | No | RAG vector store path (use `/var/data/chroma` with disk) |
| `RAG_SIMILARITY_THRESHOLD` | No | Default `0.4` |
| `ALLOW_MOCK_LLM` | No | Default `true`; set `false` in production |

4. **Persistent disk** (recommended):
   - Mount path: `/var/data`
   - Size: 1 GB
   - Set `DATABASE_URL` = `sqlite:////var/data/smartllm_router.db`

   Without a disk, SQLite and ChromaDB live on ephemeral storage and **reset on redeploy**.

   For RAG persistence, also set `CHROMA_PERSIST_DIR=/var/data/chroma`.

---

## Environment variables

All secrets are read from `os.environ` (set in Render dashboard or `render.yaml`). `python-dotenv` loads `backend/.env` locally only.

| Variable | Used by |
|----------|---------|
| `GROQ_API_KEY` | Groq LLM calls, classifier, enhancer, title; Groq model sync |
| `OPENAI_API_KEY` | OpenAI model routing via LiteLLM |
| `ANTHROPIC_API_KEY` | Anthropic model routing via LiteLLM |
| `GEMINI_API_KEY` | Google API key validation |
| `JWT_SECRET` | `auth_service.py` |
| `JWT_EXPIRE_HOURS` | Token lifetime |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Admin seed on startup |
| `DATABASE_URL` | `database.py` |
| `CORS_ORIGINS` | `main.py` CORS middleware |
| `CHROMA_PERSIST_DIR` | `vector_store.py` — RAG embeddings |
| `RAG_SIMILARITY_THRESHOLD` | `rag_service.py` |
| `API_KEY_ENCRYPTION_SECRET` | `key_encryption.py` |
| `ALLOW_MOCK_LLM` | `model_clients.py` — mock when no key |

---

## Health check

```bash
curl https://your-service.onrender.com/health
```

Example response:

```json
{
  "status": "ok",
  "service": "TokenMaxx",
  "version": "0.6.0",
  "database": { "status": "ok" },
  "groq_configured": true
}
```

Render uses `/health` for deploy health checks. `status: "degraded"` means the DB probe failed.

---

## Connect the frontend

After the API is live:

1. Note the Render URL, e.g. `https://tokenmaxx-api.onrender.com`
2. Set on your frontend host:
   ```
   VITE_API_BASE=https://tokenmaxx-api.onrender.com
   ```
3. Set on the backend:
   ```
   CORS_ORIGINS=https://your-frontend-url.onrender.com
   ```
4. Redeploy both services.

---

## Local verification (before deploy)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY, JWT_SECRET
uvicorn main:app --host 0.0.0.0 --port 8001
curl http://127.0.0.1:8001/health
```

Run tests with dev dependencies:

```bash
pip install -r requirements-dev.txt
pytest -v
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS errors in browser | Set `CORS_ORIGINS` to exact frontend URL (no trailing slash) |
| 401 on all routes | Sign up/login again; ensure `JWT_SECRET` is stable across deploys |
| Data lost after redeploy | Attach persistent disk + `DATABASE_URL=sqlite:////var/data/smartllm_router.db` + `CHROMA_PERSIST_DIR=/var/data/chroma` |
| Cold start slow (free tier) | First request after idle may take 30–60s |
| Build fails | Confirm **Root Directory** is `backend` |
