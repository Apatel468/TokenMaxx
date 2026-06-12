/**
 * Chat API — send messages with optional conversation_id for multi-turn memory.
 */
import { authFetch } from "./http.js";

/**
 * @param {string} prompt
 * @param {number|null} conversationId - omit or null to start a new thread
 * @param {boolean} enhancePrompt - user's prompt enhancement preference
 */
export async function sendChat(prompt, conversationId = null, enhancePrompt = true) {
  const body = { prompt, enhance_prompt: enhancePrompt };
  if (conversationId != null) {
    body.conversation_id = conversationId;
  }

  return authFetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/**
 * POST /chat/regenerate — retry with a user-selected model (on-demand only).
 */
export async function regenerateChat(conversationId, messageId, modelId) {
  return authFetch("/chat/regenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: conversationId,
      message_id: messageId,
      model_id: modelId,
    }),
  });
}
