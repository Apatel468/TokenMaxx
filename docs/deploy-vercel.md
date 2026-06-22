# Deploy TokenMaxx Frontend to Vercel

The React/Vite app lives in `frontend/`. The FastAPI backend is deployed separately (see [deploy-render.md](deploy-render.md)).

---

## Vercel project settings

| Setting | Value |
|---------|-------|
| **Framework Preset** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

---

## Required environment variable

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `VITE_API_BASE` | **Yes** | `https://tokenmaxx-api.onrender.com` | Deployed FastAPI URL — **no trailing slash** |

Vite embeds `VITE_API_BASE` at **build time**. After changing it in Vercel, trigger a **redeploy**.

### Optional (local dev only)

Copy `frontend/.env.example` to `frontend/.env.local`:

```
VITE_API_BASE=http://127.0.0.1:8001
```

---

## Deploy steps

### Option A — Vercel Dashboard

1. Push the repo to GitHub.
2. [vercel.com/new](https://vercel.com/new) → Import the repository.
3. Set **Root Directory** to `frontend`.
4. Add environment variable:
   - `VITE_API_BASE` = your Render (or other) API URL
5. Deploy.

### Option B — Vercel CLI

```bash
cd frontend
npm install -g vercel   # once
vercel login
vercel --prod
# Set VITE_API_BASE when prompted, or in the Vercel dashboard first
```

---

## Backend CORS

The API must allow your Vercel origin. On the backend (Render), set:

```
CORS_ORIGINS=https://your-app.vercel.app
```

For preview deployments, add comma-separated URLs:

```
CORS_ORIGINS=https://your-app.vercel.app,https://your-app-*.vercel.app
```

(Render may not support wildcards — add specific preview URLs as needed.)

---

## Routing (no React Router)

TokenMaxx uses **tab state** in `App.jsx` (Chat, Analytics, Documents, Logs, Model Controls, Admin) — not React Router and not URL paths.

`frontend/vercel.json` includes an SPA rewrite so direct visits to any path still serve `index.html`. This future-proofs the app if URL routing is added later.

After deploy, the app loads at `/` and tabs switch without page reloads.

---

## Verify `VITE_API_BASE`

All API calls go through `frontend/src/api/config.js`:

```javascript
export const API_BASE = normalizeBaseUrl(import.meta.env.VITE_API_BASE);
```

Used by:

- `http.js` → `authFetch` (most endpoints)
- `auth.js` → signup/login
- `chat.js` → SSE streaming
- `sentiment.js` → async sentiment analysis
- `settings.js` → model-settings + provider-settings
- `generations.js` → download/preview generated assets

Default when unset: `http://127.0.0.1:8001` (local dev only).

---

## Pre-deploy checklist

```bash
cd frontend
npm install
VITE_API_BASE=https://your-api.example.com npm run build
npm run preview   # optional: test production build locally
```

1. Open the preview URL → login/signup works.
2. Browser DevTools → Network → API calls hit `VITE_API_BASE`, not localhost.
3. Send a chat message → streaming response + sentiment panel updates.
4. Documents tab → upload a file.
5. Model Controls → provider toggles visible (admin).
6. Logs tab → recent activity events load.
7. Analytics tab loads data.

---

## Production build

```bash
cd frontend
npm run build
```

Output: `frontend/dist/` (static HTML, JS, CSS).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| API calls go to `127.0.0.1:8001` | Set `VITE_API_BASE` in Vercel and **redeploy** |
| CORS error in browser | Set `CORS_ORIGINS` on backend to exact Vercel URL |
| Blank page after deploy | Confirm Root Directory is `frontend` and Output is `dist` |
| 404 on refresh | Ensure `vercel.json` is in `frontend/` with SPA rewrite |
| Auth works locally, fails on Vercel | Backend `JWT_SECRET` must be stable; use HTTPS API URL |

---

## Related

- [deploy-render.md](deploy-render.md) — backend on Render
- [../frontend/.env.example](../frontend/.env.example) — local env template
