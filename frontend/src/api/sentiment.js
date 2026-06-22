import { authFetch } from "./http.js";

/**
 * Analyze sentiment asynchronously (does not block chat stream).
 */
export async function analyzeSentiment({ text, conversationId, messageId }) {
  const body = { text };
  if (conversationId != null) body.conversation_id = conversationId;
  if (messageId != null) body.message_id = messageId;

  return authFetch("/sentiment/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/**
 * Persist a prior analysis result after the chat turn is saved.
 */
export async function storeSentiment({
  messageId,
  conversationId,
  label,
  confidence,
  explanation,
  method = "rules",
}) {
  return authFetch("/sentiment/store", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message_id: messageId,
      conversation_id: conversationId,
      label,
      confidence,
      explanation,
      method,
    }),
  });
}

export async function fetchSentimentHistory(conversationId) {
  return authFetch(`/sentiment/conversations/${conversationId}/history`);
}
