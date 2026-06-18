/**
 * LogsPage — grouped activity logs by chat request / action.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchAdminLogs, fetchMyLogs } from "../api/logs.js";
import {
  formatLogTimeShort,
  groupActivityLogs,
} from "../utils/groupActivityLogs.js";

const LEVELS = ["", "info", "warning", "error"];

function statusClass(status) {
  if (status === "error") return "logs-status logs-status--error";
  if (status === "in_progress") return "logs-status logs-status--progress";
  return "logs-status logs-status--success";
}

function statusLabel(status) {
  if (status === "error") return "Error";
  if (status === "in_progress") return "In progress";
  return "Success";
}

function levelClass(level) {
  if (level === "error") return "logs-level logs-level--error";
  if (level === "warning") return "logs-level logs-level--warning";
  return "logs-level logs-level--info";
}

function kindLabel(kind) {
  if (kind === "regenerate") return "Regenerate";
  if (kind === "document") return "Document";
  if (kind === "chat") return "Chat";
  return "Activity";
}

function LogEventRow({ event, showMeta, onToggleMeta }) {
  const meta = event.metadata || {};
  const hasMeta = Object.keys(meta).length > 0;
  const modelProvider = [meta.model, meta.provider].filter(Boolean).join(" · ");

  return (
    <li className="logs-timeline__item">
      <div className="logs-timeline__row">
        <span className="logs-timeline__time">{formatLogTimeShort(event.created_at)}</span>
        <span className={levelClass(event.level)}>{event.level}</span>
        <span className="logs-timeline__event">{event.event_type}</span>
        <span className="logs-timeline__message">{event.message}</span>
        {modelProvider && (
          <span className="logs-timeline__meta">{modelProvider}</span>
        )}
        {hasMeta && (
          <button
            type="button"
            className="logs-timeline__meta-btn"
            onClick={() => onToggleMeta(event.id)}
          >
            {showMeta ? "Hide meta" : "Meta"}
          </button>
        )}
      </div>
      {showMeta && hasMeta && (
        <pre className="logs-metadata logs-metadata--inline">
          {JSON.stringify(meta, null, 2)}
        </pre>
      )}
    </li>
  );
}

function LogGroupCard({ group, isAdmin, expanded, onToggle }) {
  const [expandedMetaId, setExpandedMetaId] = useState(null);

  const title =
    group.kind === "regenerate"
      ? `Regenerate: ${group.promptPreview}`
      : group.promptPreview;

  return (
    <article className="logs-group-card">
      <div className="logs-group-card__summary">
        <div className="logs-group-card__main">
          <div className="logs-group-card__top">
            <span className="logs-group-card__kind">{kindLabel(group.kind)}</span>
            <time className="logs-group-card__time">{group.timestamp}</time>
            {isAdmin && group.userEmail && (
              <span className="logs-group-card__user">{group.userEmail}</span>
            )}
          </div>
          <p className="logs-group-card__prompt">{title}</p>
          <div className="logs-group-card__stats">
            <span className={statusClass(group.status)}>
              {statusLabel(group.status)}
            </span>
            {group.model && (
              <span className="logs-group-card__stat">
                Model: <strong>{group.model}</strong>
              </span>
            )}
            {group.provider && (
              <span className="logs-group-card__stat">
                Provider: <strong>{group.provider}</strong>
              </span>
            )}
            <span className="logs-group-card__stat">
              Events: <strong>{group.eventCount}</strong>
            </span>
          </div>
        </div>
        <button
          type="button"
          className="documents-refresh logs-group-card__toggle"
          onClick={onToggle}
          aria-expanded={expanded}
        >
          {expanded ? "Hide Timeline" : "View Timeline"}
        </button>
      </div>

      {expanded && (
        <ol className="logs-timeline">
          {group.events.map((event) => (
            <LogEventRow
              key={event.id}
              event={event}
              showMeta={expandedMetaId === event.id}
              onToggleMeta={(id) =>
                setExpandedMetaId((current) => (current === id ? null : id))
              }
            />
          ))}
        </ol>
      )}
    </article>
  );
}

function LogsPage({ isAdmin = false }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedGroupId, setExpandedGroupId] = useState(null);
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

  const groups = useMemo(() => groupActivityLogs(logs), [logs]);

  return (
    <div className="logs-page">
      <header className="documents-header">
        <div>
          <h2 className="documents-header__title">Activity Logs</h2>
          <p className="documents-header__subtitle">
            Grouped by chat request — expand a card to see the full pipeline timeline.
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
        ) : groups.length === 0 ? (
          <p className="documents-empty">No logs match your filters.</p>
        ) : (
          <div className="logs-groups">
            {groups.map((group) => (
              <LogGroupCard
                key={`${group.id}-${group.timestamp}`}
                group={group}
                isAdmin={isAdmin && adminView}
                expanded={expandedGroupId === group.id}
                onToggle={() =>
                  setExpandedGroupId((current) =>
                    current === group.id ? null : group.id
                  )
                }
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default LogsPage;
