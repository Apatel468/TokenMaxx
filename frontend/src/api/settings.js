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
  const providerEnabled = boolFromApi(model.provider_enabled, true);
  const adminEnabled = boolFromApi(model.admin_enabled, true);
  const userEnabled = boolFromApi(model.user_enabled, true);
  const available = boolFromApi(
    model.available,
    providerEnabled && adminEnabled && userEnabled,
  );
  const disabledByProvider = boolFromApi(
    model.disabled_by_provider,
    !providerEnabled,
  );
  const disabledByAdmin = boolFromApi(model.disabled_by_admin, !adminEnabled);
  const toggleEnabled = isAdmin
    ? boolFromApi(model.toggle_enabled, providerEnabled && adminEnabled)
    : boolFromApi(
        model.toggle_enabled,
        providerEnabled && userEnabled && adminEnabled,
      );

  return {
    ...model,
    provider_enabled: providerEnabled,
    admin_enabled: adminEnabled,
    user_enabled: userEnabled,
    available,
    enabled: available,
    disabled_by_provider: disabledByProvider,
    disabled_by_admin: disabledByAdmin,
    toggle_enabled: toggleEnabled,
  };
}

export function applyProviderStateToModels(models, providers, isAdmin) {
  const providerMap = Object.fromEntries(
    providers.map((provider) => [provider.provider, provider.enabled]),
  );

  return models.map((model) =>
    normalizeModelRow(
      {
        ...model,
        provider_enabled: providerMap[model.provider] ?? true,
        disabled_by_provider: !(providerMap[model.provider] ?? true),
      },
      isAdmin,
    ),
  );
}

export function buildProviderSettingsPayload(providers) {
  return {
    providers: providers.map((provider) => ({
      provider: provider.provider,
      enabled: Boolean(provider.enabled),
    })),
  };
}

export function buildModelControlsPayload(models, isAdmin) {
  return models.map((m) => ({
    model_id: String(m.model_id),
    enabled: Boolean(isAdmin ? m.admin_enabled : m.user_enabled),
  }));
}

/** GET /provider-settings */
export async function fetchProviderSettings() {
  const data = await authFetch("/provider-settings");
  return {
    providers: Array.isArray(data?.providers) ? data.providers : [],
  };
}

/** PUT /provider-settings — admin only */
export async function saveProviderSettings(providers) {
  const payload = buildProviderSettingsPayload(providers);
  const data = await authFetch("/provider-settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return {
    providers: Array.isArray(data?.providers) ? data.providers : [],
  };
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

/** Admin save: provider toggles + model toggles */
export async function saveModelAndProviderControls(
  models,
  providers,
  isAdmin = false,
) {
  if (isAdmin) {
    await saveProviderSettings(providers);
  }
  return saveModelControls(models, isAdmin);
}
