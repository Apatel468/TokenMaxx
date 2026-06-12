/**
 * User preferences API — GET/PUT /user/preferences
 */
import { authFetch } from "./http.js";

/** GET /user/preferences — defaults to { enhance_prompts: true } on failure */
export async function fetchPreferences() {
  try {
    return await authFetch("/user/preferences");
  } catch {
    return { enhance_prompts: true };
  }
}

/** PUT /user/preferences — save immediately on toggle */
export async function savePreferences({ enhance_prompts }) {
  return authFetch("/user/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enhance_prompts }),
  });
}
