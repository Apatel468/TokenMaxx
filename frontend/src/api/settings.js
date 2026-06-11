/**
 * Model Controls API — GET/PUT /model-settings
 *
 * Backend returns every routable model with admin_enabled, user_enabled,
 * and available (admin_enabled && user_enabled). Never 404 when tables are empty.
 */
import { authFetch } from "./http.js";

const MODEL_SETTINGS_PATH = "/model-settings";

function parseSettingsError(body, status, fallback) {
  if (!body?.detail) {
    if (status === 404) {
      return "Model settings endpoint not found. Restart the backend.";
    }
    return fallback;
  }
  if (typeof body.detail === "string") {
    if (body.detail === "Not Found" || status === 404) {
      return "Model settings endpoint not found. Restart the backend.";
    }
    return body.detail;
  }
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((item) => item.msg || item.message || "Invalid model settings.")
      .join(" ");
  }
  return fallback;
}

function boolFromApi(value, defaultIfMissing = true) {
  if (value === undefined || value === null) return defaultIfMissing;
  return Boolean(value);
}

/** Normalize one row from GET /model-settings. */
export function normalizeModelRow(model, isAdmin) {
  const adminEnabled = boolFromApi(model.admin_enabled, true);
  const userEnabled = boolFromApi(model.user_enabled, true);
  const available = boolFromApi(
    model.available,
    adminEnabled && userEnabled,
  );
  const disabledByAdmin = boolFromApi(model.disabled_by_admin, !adminEnabled);
  const toggleEnabled = isAdmin
    ? boolFromApi(model.toggle_enabled, adminEnabled)
    : boolFromApi(model.toggle_enabled, userEnabled);

  return {
    ...model,
    admin_enabled: adminEnabled,
    user_enabled: userEnabled,
    available,
    enabled: available,
    disabled_by_admin: disabledByAdmin,
    toggle_enabled: toggleEnabled,
  };
}

export function buildModelControlsPayload(models, isAdmin) {
  return models.map((m) => ({
    model_id: String(m.model_id),
    enabled: Boolean(isAdmin ? m.admin_enabled : m.user_enabled),
  }));
}

/** GET /model-settings */
export async function fetchModelControls(isAdmin = false) {
  const data = await authFetch(MODEL_SETTINGS_PATH);
  const rows = Array.isArray(data) ? data : [];
  return {
    models: rows.map((row) => normalizeModelRow(row, isAdmin)),
    warning: null,
  };
}

/** PUT /model-settings — admins save org-wide; users save personal prefs */
export async function saveModelControls(models, isAdmin = false) {
  const payload = { models: buildModelControlsPayload(models, isAdmin) };
  await authFetch(MODEL_SETTINGS_PATH, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return fetchModelControls(isAdmin);
}
