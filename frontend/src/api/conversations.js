/**
 * Conversation API — list and load multi-turn threads.
 */
import { API_BASE } from "./config.js";

async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

/** GET /conversations — list recent threads */
export function fetchConversations(limit = 50) {
  return fetchJson(`/conversations?limit=${limit}`);
}

/** GET /conversations/{id} — full message history */
export function fetchConversation(conversationId) {
  return fetchJson(`/conversations/${conversationId}`);
}
