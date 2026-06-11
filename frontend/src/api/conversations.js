/**
 * Conversation API — list and load multi-turn threads.
 */
import { authFetch } from "./http.js";

/** GET /conversations — list recent threads */
export function fetchConversations(limit = 50) {
  return authFetch(`/conversations?limit=${limit}`);
}

/** GET /conversations/{id} — full message history */
export function fetchConversation(conversationId) {
  return authFetch(`/conversations/${conversationId}`);
}
