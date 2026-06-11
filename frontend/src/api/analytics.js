/**
 * Analytics API helpers — fetch SQLite stats from the backend (scoped to logged-in user).
 */
import { authFetch } from "./http.js";

/** GET /analytics/summary — totals for the dashboard cards */
export function fetchSummary() {
  return authFetch("/analytics/summary");
}

/** GET /analytics/history — recent chat rows */
export function fetchHistory(limit = 20) {
  return authFetch(`/analytics/history?limit=${limit}`);
}

/** GET /analytics/model-usage — per-model breakdown */
export function fetchModelUsage() {
  return authFetch("/analytics/model-usage");
}
