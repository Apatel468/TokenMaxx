/**
 * LogsPage — activity logs for debugging routing, RAG, and model calls.
 */
import { Fragment, useCallback, useEffect, useState } from "react";
import { fetchAdminLogs, fetchMyLogs } from "../api/logs.js";

const LEVELS = ["", "info", "warning", "error"];

function LogsPage({ isAdmin = false }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [adminView, setAdminView] = useState(false);
  const [filters, setFilters] = useState({
    event_type: "",
    level: "",
    provider: "",
    model: "",
    start_date: "",
    end_date: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows =
        isAdmin && adminView
          ? await fetchAdminLogs({ ...filters, limit: 200 })
          : await fetchMyLogs({ ...filters, limit: 100 });
      setLogs(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setError(err.message || "Could not load logs.");
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [filters, isAdmin, adminView]);

  useEffect(() => {
    load();
  }, [load]);

  function levelClass(level) {
    if (level === "error") return "logs-level logs-level--error";
    if (level === "warning") return "logs-level logs-level--warning";
    return "logs-level logs-level--info";
  }

  return (
    <div className="logs-page">
      <header className="documents-header">
        <div>
          <h2 className="documents-header__title">Activity Logs</h2>
          <p className="documents-header__subtitle">
            Timestamped backend events for routing, RAG, prompt enhancement, and model calls.
          </p>
        </div>
        <div className="logs-header__actions">
          {isAdmin && (
            <button
              type="button"
              className={`documents-refresh ${adminView ? "documents-refresh--active" : ""}`}
              onClick={() => setAdminView((v) => !v)}
            >
              {adminView ? "All users" : "My logs"}
            </button>
          )}
          <button type="button" className="documents-refresh" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>
      </header>

      <section className="logs-filters panel">
        <div className="logs-filters__grid">
          <label>
            Event type
            <input
              type="text"
              placeholder="e.g. model_call_completed"
              value={filters.event_type}
              onChange={(e) => setFilters((f) => ({ ...f, event_type: e.target.value }))}
            />
          </label>
          <label>
            Level
            <select
              value={filters.level}
              onChange={(e) => setFilters((f) => ({ ...f, level: e.target.value }))}
            >
              {LEVELS.map((level) => (
                <option key={level || "all"} value={level}>
                  {level || "All"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Provider
            <input
              type="text"
              placeholder="groq"
              value={filters.provider}
              onChange={(e) => setFilters((f) => ({ ...f, provider: e.target.value }))}
            />
          </label>
          <label>
            Model
            <input
              type="text"
              placeholder="model id"
              value={filters.model}
              onChange={(e) => setFilters((f) => ({ ...f, model: e.target.value }))}
            />
          </label>
          <label>
            Start date
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))}
            />
          </label>
          <label>
            End date
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))}
            />
          </label>
        </div>
        <button type="button" className="api-keys-form__submit" onClick={load}>
          Apply filters
        </button>
      </section>

      {error && <div className="alert alert--error">{error}</div>}

      <section className="logs-list panel">
        {loading ? (
          <div className="documents-loading">
            <div className="spinner" />
            <p>Loading logs…</p>
          </div>
        ) : logs.length === 0 ? (
          <p className="documents-empty">No logs match your filters.</p>
        ) : (
          <div className="logs-table-wrap">
            <table className="logs-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Level</th>
                  <th>Event</th>
                  <th>Message</th>
                  <th>Model / Provider</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {logs.map((row) => {
                  const meta = row.metadata || {};
                  const modelProvider = [meta.model, meta.provider].filter(Boolean).join(" · ");
                  return (
                    <Fragment key={row.id}>
                      <tr>
                        <td className="logs-table__time">{row.created_at}</td>
                        <td>
                          <span className={levelClass(row.level)}>{row.level}</span>
                        </td>
                        <td className="logs-table__event">{row.event_type}</td>
                        <td>{row.message}</td>
                        <td className="logs-table__meta">{modelProvider || "—"}</td>
                        <td>
                          <button
                            type="button"
                            className="documents-refresh"
                            onClick={() =>
                              setExpandedId((id) => (id === row.id ? null : row.id))
                            }
                          >
                            {expandedId === row.id ? "Hide" : "Details"}
                          </button>
                        </td>
                      </tr>
                      {expandedId === row.id && (
                        <tr className="logs-table__expand">
                          <td colSpan={6}>
                            <pre className="logs-metadata">
                              {JSON.stringify(row.metadata || {}, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default LogsPage;
