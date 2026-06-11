/**
 * Settings API — Model Controls enable/disable toggles.
 */
import { API_BASE } from "./config.js";

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) {
        message =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      // keep generic message
    }
    throw new Error(message);
  }
  return response.json();
}

/** GET /settings/models */
export function fetchModelControls() {
  return fetchJson("/settings/models");
}

/** PUT /settings/models */
export function saveModelControls(models) {
  return fetchJson("/settings/models", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ models }),
  });
}
