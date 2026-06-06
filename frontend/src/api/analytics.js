/**
 * Analytics API helpers — fetch SQLite stats from the backend.
 */
import { API_BASE } from "./config.js";

async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Analytics request failed (${response.status})`);
  }
  return response.json();
}

/** GET /analytics/summary — totals for the dashboard cards */
export function fetchSummary() {
  return fetchJson("/analytics/summary");
}

/** GET /analytics/history — recent chat rows */
export function fetchHistory(limit = 20) {
  return fetchJson(`/analytics/history?limit=${limit}`);
}

/** GET /analytics/model-usage — per-model breakdown */
export function fetchModelUsage() {
  return fetchJson("/analytics/model-usage");
}
