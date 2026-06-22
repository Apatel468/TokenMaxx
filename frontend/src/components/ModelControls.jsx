/**
 * Model Controls — GET/PUT /model-settings + /provider-settings
 * available = provider_enabled && admin_enabled && user_enabled
 */
import { useCallback, useEffect, useState } from "react";
import { savePreferences } from "../api/preferences.js";
import {
  applyProviderStateToModels,
  fetchModelControls,
  fetchProviderSettings,
  normalizeModelRow,
  saveModelAndProviderControls,
} from "../api/settings.js";
import ApiKeysSection from "./ApiKeysSection.jsx";

function tierLabel(tier) {
  if (tier === "economy") return "Economy";
  if (tier === "standard") return "Standard";
  return tier;
}

function providerLabel(provider) {
  const labels = {
    groq: "Groq",
    openai: "OpenAI",
    anthropic: "Anthropic",
    google: "Google",
  };
  return labels[provider] || provider;
}

function ModelControls({
  isAdmin = false,
  enhancePrompts = true,
  onEnhancePromptsChange,
}) {
  const [models, setModels] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [prefSaving, setPrefSaving] = useState(false);
  const [error, setError] = useState(null);
  const [prefError, setPrefError] = useState(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [modelResult, providerResult] = await Promise.all([
        fetchModelControls(isAdmin),
        fetchProviderSettings(),
      ]);
      setProviders(providerResult.providers);
      setModels(
        applyProviderStateToModels(
          modelResult.models,
          providerResult.providers,
          isAdmin,
        ),
      );
    } catch (err) {
      setError(err.message || "Could not load model settings.");
      setModels([]);
      setProviders([]);
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  function toggleProvider(providerName) {
    if (!isAdmin) return;

    setSaved(false);
    setProviders((prev) => {
      const next = prev.map((provider) =>
        provider.provider === providerName
          ? { ...provider, enabled: !provider.enabled }
          : provider,
      );
      setModels((currentModels) =>
        applyProviderStateToModels(currentModels, next, true),
      );
      return next;
    });
  }

  function toggleModel(modelId) {
    setSaved(false);
    setModels((prev) =>
      prev.map((m) => {
        if (m.model_id !== modelId) return m;

        if (!m.provider_enabled) return m;

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

  async function handleEnhanceToggle() {
    const next = !enhancePrompts;
    setPrefSaving(true);
    setPrefError(null);
    try {
      const result = await savePreferences({ enhance_prompts: next });
      onEnhancePromptsChange?.(result.enhance_prompts ?? next);
    } catch (err) {
      setPrefError(err.message || "Could not save preference.");
    } finally {
      setPrefSaving(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const result = await saveModelAndProviderControls(
        models,
        providers,
        isAdmin,
      );
      const providerResult = await fetchProviderSettings();
      setProviders(providerResult.providers);
      setModels(
        applyProviderStateToModels(
          result.models,
          providerResult.providers,
          isAdmin,
        ),
      );
      setSaved(true);
    } catch (err) {
      setError(err.message || "Could not save model settings.");
    } finally {
      setSaving(false);
    }
  }

  const enabledCount = isAdmin
    ? models.filter((m) => m.provider_enabled && m.admin_enabled).length
    : models.filter((m) => m.available).length;

  const modelsByProvider = providers.map((provider) => ({
    ...provider,
    models: models.filter((model) => model.provider === provider.provider),
  }));

  return (
    <div className="settings-page">
      <header className="settings-header">
        <div>
          <h2 className="settings-header__title">Model Controls</h2>
          <p className="settings-header__subtitle">
            {isAdmin
              ? "Disable entire providers or individual models organization-wide."
              : "Your personal model preferences on top of admin settings. A model is used only when enabled by provider, admin, and you."}
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
      {prefError && <div className="alert alert--error">{prefError}</div>}
      {saved && (
        <div className="alert alert--success">Model preferences saved.</div>
      )}

      <section className="preference-card">
        <div className="preference-card__info">
          <h3 className="preference-card__title">Prompt Enhancement</h3>
          <p className="preference-card__desc">
            Improve prompts before routing. May increase quality but adds cost
            and latency.
          </p>
        </div>
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={enhancePrompts}
            disabled={prefSaving}
            onChange={handleEnhanceToggle}
          />
          <span className="toggle-switch__track" />
          <span className="toggle-switch__label">
            {prefSaving ? "Saving…" : enhancePrompts ? "ON" : "OFF"}
          </span>
        </label>
      </section>

      {loading ? (
        <div className="settings-loading">
          <div className="spinner" />
          <p>Loading models…</p>
        </div>
      ) : models.length === 0 ? (
        <p className="settings-summary">
          No models found. Check VITE_API_BASE and restart the backend.
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

          <section className="provider-controls panel">
            <h3 className="provider-controls__title">Providers</h3>
            <p className="provider-controls__hint">
              {isAdmin
                ? "Disable a provider to turn off all of its models at once."
                : "Provider availability is controlled by your administrator."}
            </p>
            <div className="provider-controls__list">
              {providers.map((provider) => (
                <label
                  key={provider.provider}
                  className={`provider-control-row ${
                    provider.enabled ? "" : "provider-control-row--disabled"
                  }`}
                  title={
                    !isAdmin && !provider.enabled
                      ? "Disabled by administrator"
                      : undefined
                  }
                >
                  <input
                    type="checkbox"
                    checked={Boolean(provider.enabled)}
                    disabled={!isAdmin}
                    onChange={() => toggleProvider(provider.provider)}
                  />
                  <span className="provider-control-row__label">
                    <span
                      className={`provider-badge provider-badge--${provider.provider}`}
                    >
                      {providerLabel(provider.provider)}
                    </span>
                    <span className="provider-control-row__count">
                      ({provider.model_count} model
                      {provider.model_count === 1 ? "" : "s"})
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </section>

          <div className="provider-model-groups">
            {modelsByProvider.map((group) => (
              <section
                key={group.provider}
                className={`provider-model-group ${
                  group.enabled ? "" : "provider-model-group--disabled"
                }`}
              >
                <header className="provider-model-group__header">
                  <h3 className="provider-model-group__title">
                    {providerLabel(group.provider)}
                  </h3>
                  <span className="provider-model-group__count">
                    {group.models.length} model
                    {group.models.length === 1 ? "" : "s"}
                  </span>
                  {!group.enabled && (
                    <span className="provider-model-group__status">
                      {isAdmin
                        ? "Disabled by provider setting"
                        : "Disabled by administrator"}
                    </span>
                  )}
                </header>

                <div className="model-controls-list">
                  {group.models.map((model) => {
                    const lockedByProvider = !model.provider_enabled;
                    const lockedByAdmin =
                      !isAdmin && model.disabled_by_admin && !lockedByProvider;
                    const locked = lockedByProvider || lockedByAdmin;
                    const isOn = isAdmin
                      ? model.admin_enabled
                      : model.user_enabled;
                    const checked = locked ? false : isOn;
                    const lockMessage = lockedByProvider
                      ? isAdmin
                        ? "Disabled by provider setting"
                        : "Disabled by administrator"
                      : "Disabled by admin";

                    return (
                      <div
                        key={model.model_id}
                        className={`model-control-card ${
                          checked && model.provider_enabled
                            ? ""
                            : "model-control-card--disabled"
                        } ${locked ? "model-control-card--admin-locked" : ""}`}
                        title={
                          lockedByProvider && !isAdmin
                            ? "Disabled by administrator"
                            : undefined
                        }
                      >
                        <div className="model-control-card__info">
                          <div className="model-control-card__top">
                            <h3 className="model-control-card__name">
                              {model.name}
                            </h3>
                            <div className="model-control-card__badges">
                              <span
                                className={`provider-badge provider-badge--${model.provider}`}
                              >
                                {providerLabel(model.provider)}
                              </span>
                              <span
                                className={`tier-badge tier-badge--${model.tier}`}
                              >
                                {tierLabel(model.tier)}
                              </span>
                            </div>
                          </div>
                          <p className="model-control-card__meta">
                            <span>{model.model_id}</span>
                          </p>
                          <p className="model-control-card__tasks">
                            Tasks: {(model.task_types || []).join(", ")}
                          </p>
                          <p className="model-control-card__cost">
                            ${Number(model.cost_per_1k_input).toFixed(5)} in / $
                            {Number(model.cost_per_1k_output).toFixed(5)} out per
                            1K tokens
                          </p>
                          {locked && (
                            <p className="model-control-card__admin-lock">
                              {lockMessage}
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
                            {locked ? lockMessage : checked ? "Enabled" : "Disabled"}
                          </span>
                        </label>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        </>
      )}

      <ApiKeysSection />
    </div>
  );
}

export default ModelControls;
