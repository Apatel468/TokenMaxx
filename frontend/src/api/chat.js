/**
 * Chat API — send messages with optional conversation_id for multi-turn memory.
 */
import { authFetch } from "./http.js";

/**
 * @param {string} prompt
 * @param {number|null} conversationId - omit or null to start a new thread
 */
export async function sendChat(prompt, conversationId = null) {
  const body = { prompt };
  if (conversationId != null) {
    body.conversation_id = conversationId;
  }

  return authFetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
