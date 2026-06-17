/**
 * User API keys API.
 */
import { authFetch } from "./http.js";

export const API_KEY_PROVIDERS = [
  { id: "groq", label: "Groq" },
  { id: "openai", label: "OpenAI" },
  { id: "anthropic", label: "Anthropic" },
  { id: "google", label: "Google Gemini" },
  { id: "bedrock", label: "AWS Bedrock (placeholder)" },
];

export function fetchApiKeys() {
  return authFetch("/user/api-keys");
}

export function createApiKey({ provider, api_key, key_label, is_active = true }) {
  return authFetch("/user/api-keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key, key_label, is_active }),
  });
}

export function updateApiKey(id, payload) {
  return authFetch(`/user/api-keys/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteApiKey(id) {
  return authFetch(`/user/api-keys/${id}`, { method: "DELETE" });
}

export function testApiKey(id) {
  return authFetch(`/user/api-keys/${id}/test`, { method: "POST" });
}
