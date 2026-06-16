/**
 * Chat API — send messages with optional conversation_id for multi-turn memory.
 */
import { API_BASE } from "./config.js";
import { authFetch, getToken } from "./http.js";

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
 * Parse buffered SSE text into discrete events. Returns { events, remainder }.
 */
function parseSseBuffer(buffer) {
  const events = [];
  const parts = buffer.split("\n\n");
  const remainder = parts.pop() ?? "";

  for (const block of parts) {
    if (!block.trim()) continue;

    let eventType = "message";
    let data = "";

    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        data += line.slice(5).trim();
      }
    }

    if (!data) continue;

    try {
      events.push({ event: eventType, data: JSON.parse(data) });
    } catch {
      events.push({ event: eventType, data });
    }
  }

  return { events, remainder };
}

/**
 * Stream a chat response via POST /chat/stream (Server-Sent Events).
 *
 * @param {object} params
 * @param {string} params.prompt
 * @param {number|null} [params.conversationId]
 * @param {boolean} [params.enhancePrompt]
 * @param {(data: object) => void} [params.onRoutingStart]
 * @param {(data: object) => void} [params.onRoutingComplete]
 * @param {(data: { content: string }) => void} [params.onToken]
 * @param {(data: object) => void} [params.onComplete]
 * @param {(data: { message: string }) => void} [params.onError]
 */
export async function streamChat({
  prompt,
  conversationId = null,
  enhancePrompt = true,
  onRoutingStart,
  onRoutingComplete,
  onToken,
  onComplete,
  onError,
}) {
  const body = { prompt, enhance_prompt: enhancePrompt };
  if (conversationId != null) {
    body.conversation_id = conversationId;
  }

  const token = getToken();
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers,
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

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Streaming is not supported in this browser.");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseBuffer(buffer);
    buffer = parsed.remainder;

    for (const { event, data } of parsed.events) {
      switch (event) {
        case "routing_start":
          onRoutingStart?.(data);
          break;
        case "routing_complete":
          onRoutingComplete?.(data);
          break;
        case "token":
          onToken?.(data);
          break;
        case "complete":
          onComplete?.(data);
          break;
        case "error":
          onError?.(data);
          throw new Error(data?.message || "Streaming failed.");
        default:
          break;
      }
    }
  }

  if (buffer.trim()) {
    const parsed = parseSseBuffer(`${buffer}\n\n`);
    for (const { event, data } of parsed.events) {
      if (event === "complete") onComplete?.(data);
      if (event === "error") {
        onError?.(data);
        throw new Error(data?.message || "Streaming failed.");
      }
    }
  }
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
