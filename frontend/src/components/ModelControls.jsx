/**
 * Model Controls — enable/disable routable Groq models for TokenMaxx.
 */
import { useCallback, useEffect, useState } from "react";
import { fetchModelControls, saveModelControls } from "../api/settings.js";

function tierLabel(tier) {
  if (tier === "economy") return "Economy";
  if (tier === "standard") return "Standard";
  return tier;
}

function ModelControls() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchModelControls();
      setModels(data);
    } catch (err) {
      setError(err.message || "Could not load model settings.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function toggleModel(modelId) {
    setSaved(false);
    setModels((prev) =>
      prev.map((m) =>
        m.model_id === modelId ? { ...m, enabled: !m.enabled } : m
      )
    );
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const payload = models.map((m) => ({
        model_id: m.model_id,
        enabled: m.enabled,
      }));
      const data = await saveModelControls(payload);
      setModels(data);
      setSaved(true);
    } catch (err) {
      setError(err.message || "Could not save model settings.");
    } finally {
      setSaving(false);
    }
  }

  const enabledCount = models.filter((m) => m.enabled).length;

  return (
    <div className="settings-page">
      <header className="settings-header">
        <div>
          <h2 className="settings-header__title">Model Controls</h2>
          <p className="settings-header__subtitle">
            Choose which models TokenMaxx is allowed to route requests to.
            Disabled models trigger intelligent fallback at chat time.
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
      ) : (
        <>
          <p className="settings-summary">
            {enabledCount} of {models.length} models enabled
            {enabledCount === 0 && (
              <span className="settings-summary__warn">
                {" "}
                — enable at least one model to use chat
              </span>
            )}
          </p>

          <div className="model-controls-list">
            {models.map((model) => (
              <div
                key={model.model_id}
                className={`model-control-card ${model.enabled ? "" : "model-control-card--disabled"}`}
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
                    Tasks: {model.task_types.join(", ")}
                  </p>
                  <p className="model-control-card__cost">
                    ${model.cost_per_1k_input.toFixed(5)} in / $
                    {model.cost_per_1k_output.toFixed(5)} out per 1K tokens
                  </p>
                </div>

                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={model.enabled}
                    onChange={() => toggleModel(model.model_id)}
                  />
                  <span className="toggle-switch__track" />
                  <span className="toggle-switch__label">
                    {model.enabled ? "Enabled" : "Disabled"}
                  </span>
                </label>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default ModelControls;
