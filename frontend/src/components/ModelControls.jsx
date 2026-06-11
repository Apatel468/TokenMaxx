/**
 * Model Controls — GET/PUT /model-settings
 * available = admin_enabled && user_enabled
 */
import { useCallback, useEffect, useState } from "react";
import {
  fetchModelControls,
  normalizeModelRow,
  saveModelControls,
} from "../api/settings.js";

function tierLabel(tier) {
  if (tier === "economy") return "Economy";
  if (tier === "standard") return "Standard";
  return tier;
}

function ModelControls({ isAdmin = false }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchModelControls(isAdmin);
      setModels(result.models);
    } catch (err) {
      setError(err.message || "Could not load model settings.");
      setModels([]);
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  function toggleModel(modelId) {
    setSaved(false);
    setModels((prev) =>
      prev.map((m) => {
        if (m.model_id !== modelId) return m;

        if (isAdmin) {
          return normalizeModelRow(
            { ...m, admin_enabled: !m.admin_enabled },
            true,
          );
        }

        if (m.disabled_by_admin) return m;

        return normalizeModelRow(
          { ...m, user_enabled: !m.user_enabled },
          false,
        );
      }),
    );
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const result = await saveModelControls(models, isAdmin);
      setModels(result.models);
      setSaved(true);
    } catch (err) {
      setError(err.message || "Could not save model settings.");
    } finally {
      setSaving(false);
    }
  }

  const enabledCount = isAdmin
    ? models.filter((m) => m.admin_enabled).length
    : models.filter((m) => m.available).length;

  return (
    <div className="settings-page">
      <header className="settings-header">
        <div>
          <h2 className="settings-header__title">Model Controls</h2>
          <p className="settings-header__subtitle">
            {isAdmin
              ? "Organization-wide model access. Disabled models are off for every user."
              : "Your personal model preferences on top of admin settings. A model is used only when enabled by both you and your admin."}
          </p>
        </div>
        <button
          type="button"
          className="settings-save-btn"
          onClick={handleSave}
          disabled={saving || loading || models.length === 0}
        >
          {saving ? "Saving…" : "Save Changes"}
        </button>
      </header>

      {error && <div className="alert alert--error">{error}</div>}
      {saved && (
        <div className="alert alert--success">Model preferences saved.</div>
      )}

      {loading ? (
        <div className="settings-loading">
          <div className="spinner" />
          <p>Loading models…</p>
        </div>
      ) : models.length === 0 ? (
        <p className="settings-summary">
          No models found. Restart the backend on port 8001.
        </p>
      ) : (
        <>
          <p className="settings-summary">
            {enabledCount} of {models.length} models{" "}
            {isAdmin ? "enabled organization-wide" : "available for you"}
            {enabledCount === 0 && (
              <span className="settings-summary__warn">
                {" "}
                — enable at least one model to use chat
              </span>
            )}
          </p>

          <div className="model-controls-list">
            {models.map((model) => {
              const locked = !isAdmin && model.disabled_by_admin;
              const isOn = isAdmin ? model.admin_enabled : model.user_enabled;
              const checked = locked ? false : isOn;

              return (
                <div
                  key={model.model_id}
                  className={`model-control-card ${
                    checked ? "" : "model-control-card--disabled"
                  } ${locked ? "model-control-card--admin-locked" : ""}`}
                >
                  <div className="model-control-card__info">
                    <div className="model-control-card__top">
                      <h3 className="model-control-card__name">{model.name}</h3>
                      <span className={`tier-badge tier-badge--${model.tier}`}>
                        {tierLabel(model.tier)}
                      </span>
                    </div>
                    <p className="model-control-card__meta">
                      <span>{model.provider}</span>
                      <span>·</span>
                      <span>{model.model_id}</span>
                    </p>
                    <p className="model-control-card__tasks">
                      Tasks: {(model.task_types || []).join(", ")}
                    </p>
                    <p className="model-control-card__cost">
                      ${Number(model.cost_per_1k_input).toFixed(5)} in / $
                      {Number(model.cost_per_1k_output).toFixed(5)} out per 1K
                      tokens
                    </p>
                    {locked && (
                      <p className="model-control-card__admin-lock">
                        Disabled by admin
                      </p>
                    )}
                  </div>

                  <label
                    className={`toggle-switch ${locked ? "toggle-switch--locked" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={locked}
                      onChange={() => toggleModel(model.model_id)}
                    />
                    <span className="toggle-switch__track" />
                    <span className="toggle-switch__label">
                      {locked
                        ? "Disabled by admin"
                        : checked
                          ? "Enabled"
                          : "Disabled"}
                    </span>
                  </label>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

export default ModelControls;
