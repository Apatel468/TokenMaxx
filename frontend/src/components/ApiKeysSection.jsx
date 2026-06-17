/**
 * API Keys section — per-user LLM provider keys (masked at rest).
 */
import { useCallback, useEffect, useState } from "react";
import {
  API_KEY_PROVIDERS,
  createApiKey,
  deleteApiKey,
  fetchApiKeys,
  testApiKey,
} from "../api/apiKeys.js";

function ApiKeysSection() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [form, setForm] = useState({
    provider: "groq",
    key_label: "",
    api_key: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchApiKeys();
      setKeys(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setError(err.message || "Could not load API keys.");
      setKeys([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAdd(event) {
    event.preventDefault();
    if (!form.api_key.trim()) {
      setError("API key is required.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await createApiKey({
        provider: form.provider,
        api_key: form.api_key.trim(),
        key_label: form.key_label.trim() || form.provider,
      });
      setForm({ provider: "groq", key_label: "", api_key: "" });
      setSuccess("API key saved. Masked key shown below.");
      await load();
    } catch (err) {
      setError(err.message || "Could not save API key.");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(keyId) {
    setTestingId(keyId);
    setError(null);
    setSuccess(null);
    try {
      const result = await testApiKey(keyId);
      setSuccess(result.message || (result.valid ? "Key is valid." : "Key test failed."));
    } catch (err) {
      setError(err.message || "Key test failed.");
    } finally {
      setTestingId(null);
    }
  }

  async function handleDelete(keyId, label) {
    if (!window.confirm(`Delete API key "${label}"?`)) return;
    setError(null);
    setSuccess(null);
    try {
      await deleteApiKey(keyId);
      setSuccess("API key deleted.");
      setKeys((prev) => prev.filter((row) => row.id !== keyId));
    } catch (err) {
      setError(err.message || "Could not delete API key.");
    }
  }

  return (
    <section className="api-keys-section panel">
      <h3 className="api-keys-section__title">API Keys</h3>
      <p className="panel__hint api-keys-section__hint">
        Add your own provider keys. TokenMaxx uses them before app-level keys.
        Full keys are never shown after saving.
      </p>

      <form className="api-keys-form" onSubmit={handleAdd}>
        <div className="api-keys-form__row">
          <label className="api-keys-form__field">
            <span>Provider</span>
            <select
              value={form.provider}
              onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
            >
              {API_KEY_PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="api-keys-form__field">
            <span>Label</span>
            <input
              type="text"
              placeholder="e.g. Work Groq"
              value={form.key_label}
              onChange={(e) => setForm((f) => ({ ...f, key_label: e.target.value }))}
            />
          </label>
        </div>
        <label className="api-keys-form__field api-keys-form__field--full">
          <span>API Key</span>
          <input
            type="password"
            placeholder="Paste key once — stored encrypted"
            value={form.api_key}
            onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
            autoComplete="off"
          />
        </label>
        <button type="submit" className="api-keys-form__submit" disabled={saving}>
          {saving ? "Saving…" : "Add API Key"}
        </button>
      </form>

      {success && <div className="alert alert--success">{success}</div>}
      {error && <div className="alert alert--error">{error}</div>}

      {loading ? (
        <div className="documents-loading">
          <div className="spinner" />
          <p>Loading API keys…</p>
        </div>
      ) : keys.length === 0 ? (
        <p className="documents-empty">No API keys yet.</p>
      ) : (
        <div className="api-keys-list">
          {keys.map((row) => (
            <div key={row.id} className="api-keys-card">
              <div>
                <div className="api-keys-card__top">
                  <strong>{row.key_label || row.provider}</strong>
                  <span className="documents-type-badge">{row.provider.toUpperCase()}</span>
                  {!row.is_active && (
                    <span className="api-keys-card__inactive">Inactive</span>
                  )}
                </div>
                <p className="api-keys-card__masked">{row.masked_key}</p>
                <p className="api-keys-card__meta">
                  Added {row.created_at}
                  {row.last_used_at ? ` · Last used ${row.last_used_at}` : ""}
                </p>
              </div>
              <div className="api-keys-card__actions">
                <button
                  type="button"
                  className="documents-refresh"
                  onClick={() => handleTest(row.id)}
                  disabled={testingId === row.id}
                >
                  {testingId === row.id ? "Testing…" : "Test"}
                </button>
                <button
                  type="button"
                  className="documents-delete-btn"
                  onClick={() => handleDelete(row.id, row.key_label || row.provider)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default ApiKeysSection;
