/**
 * Shared backend URL for all API modules.
 *
 * Set VITE_API_BASE in frontend/.env.local (dev) or your hosting provider's
 * environment (production) to the deployed FastAPI origin, e.g.:
 *   VITE_API_BASE=https://tokenmaxx-api.onrender.com
 *
 * Falls back to http://127.0.0.1:8001 when unset.
 */
const DEFAULT_API_BASE = "http://127.0.0.1:8001";

function normalizeBaseUrl(url) {
  const trimmed = (url || DEFAULT_API_BASE).trim();
  return trimmed.replace(/\/+$/, "");
}

export const API_BASE = normalizeBaseUrl(import.meta.env.VITE_API_BASE);
