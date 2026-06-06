/**
 * Chat API — send messages with optional conversation_id for multi-turn memory.
 */
import { API_BASE } from "./config.js";

/**
 * @param {string} prompt
 * @param {number|null} conversationId - omit or null to start a new thread
 */
export async function sendChat(prompt, conversationId = null) {
  const body = { prompt };
  if (conversationId != null) {
    body.conversation_id = conversationId;
  }

  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        message =
          typeof errorBody.detail === "string"
            ? errorBody.detail
            : JSON.stringify(errorBody.detail);
      }
    } catch {
      // keep generic message
    }
    throw new Error(message);
  }

  return response.json();
}
