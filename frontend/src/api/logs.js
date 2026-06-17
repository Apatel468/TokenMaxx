/**
 * Activity logs API.
 */
import { authFetch } from "./http.js";

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function fetchMyLogs(filters = {}) {
  return authFetch(`/logs/my${buildQuery(filters)}`);
}

export function fetchConversationLogs(conversationId, filters = {}) {
  return authFetch(`/logs/conversation/${conversationId}${buildQuery(filters)}`);
}

export function fetchAdminLogs(filters = {}) {
  return authFetch(`/logs/admin/logs${buildQuery(filters)}`);
}
