/**
 * AdminDashboard — employee usage + detailed per-user metrics (admin only).
 */
import { useCallback, useEffect, useState } from "react";
import { fetchAdminUserMetrics, fetchEmployeeUsage } from "../api/admin.js";
import { formatCost, formatTokenTotal } from "../utils/costMetrics.js";

function formatUsd(value) {
  return formatCost(value);
}

function MetricBreakdown({ title, items, valueKey = "count", labelKey }) {
  if (!items?.length) {
    return (
      <div className="admin-metrics-detail">
        <h4>{title}</h4>
        <p className="admin-metrics-detail__empty">No data</p>
      </div>
    );
  }

  return (
    <div className="admin-metrics-detail">
      <h4>{title}</h4>
      <ul className="admin-metrics-detail__list">
        {items.map((item) => (
          <li key={item[labelKey] || item.model || item.feature || item.category}>
            <span>{item[labelKey] || item.model || item.feature || item.category}</span>
            <strong>{item[valueKey]}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

function UserMetricsRow({ row, expanded, onToggle }) {
  return (
    <>
      <tr className={expanded ? "admin-metrics-row--expanded" : ""}>
        <td>
          <button
            type="button"
            className="admin-metrics-row__toggle"
            onClick={onToggle}
            aria-expanded={expanded}
          >
            {expanded ? "▾" : "▸"} {row.email}
          </button>
        </td>
        <td>{row.total_prompts}</td>
        <td>{row.average_prompts_per_session}</td>
        <td>{row.top_model || "—"}</td>
        <td>{row.top_category || "—"}</td>
        <td>{row.average_latency_ms ? `${row.average_latency_ms} ms` : "—"}</td>
        <td>{row.total_tokens?.toLocaleString() ?? 0}</td>
        <td>{formatUsd(row.total_actual_cost)}</td>
        <td>{formatUsd(row.total_savings)}</td>
      </tr>
      {expanded && (
        <tr className="admin-metrics-row__details">
          <td colSpan={9}>
            <div className="admin-metrics-expanded">
              <div className="admin-metrics-expanded__grid">
                <MetricBreakdown
                  title="Prompts over time"
                  items={row.prompts_over_time?.map((item) => ({
                    label: item.period,
                    count: item.count,
                  }))}
                  labelKey="label"
                />
                <MetricBreakdown
                  title="Model usage"
                  items={row.most_used_models}
                  valueKey="run_count"
                  labelKey="model"
                />
                <MetricBreakdown
                  title="Avg latency by model"
                  items={row.average_latency_by_model?.map((item) => ({
                    model: item.model,
                    count: `${item.average_latency_ms} ms`,
                  }))}
                  valueKey="count"
                  labelKey="model"
                />
                <MetricBreakdown
                  title="Feature usage"
                  items={row.feature_usage}
                  valueKey="count"
                  labelKey="feature"
                />
                <MetricBreakdown
                  title="Query categories"
                  items={row.query_categories}
                  valueKey="count"
                  labelKey="category"
                />
              </div>
              <div className="admin-metrics-expanded__summary">
                <span>Sessions: {row.session_count}</span>
                <span>Role: {row.role}</span>
                <span>Premium: {formatUsd(row.total_premium_cost)}</span>
                <span>Savings: {row.savings_percentage}%</span>
                <span>
                  Tokens: {formatTokenTotal(row.total_input_tokens, row.total_output_tokens)}
                </span>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AdminDashboard() {
  const [rows, setRows] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metricsError, setMetricsError] = useState(null);
  const [expandedUserId, setExpandedUserId] = useState(null);
  const [filters, setFilters] = useState({
    startDate: "",
    endDate: "",
    granularity: "daily",
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchEmployeeUsage();
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load employee usage");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadMetrics = useCallback(async () => {
    setMetricsLoading(true);
    setMetricsError(null);
    try {
      const data = await fetchAdminUserMetrics({
        startDate: filters.startDate || undefined,
        endDate: filters.endDate || undefined,
        granularity: filters.granularity,
      });
      setMetrics(Array.isArray(data) ? data : []);
    } catch (err) {
      setMetricsError(err.message || "Failed to load user metrics");
      setMetrics([]);
    } finally {
      setMetricsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  return (
    <div className="admin-dashboard">
      <header className="admin-dashboard__header">
        <h2>Admin Dashboard</h2>
        <p>Organization-wide usage, costs, and per-user analytics.</p>
      </header>

      <section className="admin-dashboard__section panel">
        <h3 className="admin-dashboard__section-title">Employee Usage</h3>
        {loading ? (
          <p className="admin-dashboard__status">Loading employee metrics…</p>
        ) : error ? (
          <p className="admin-dashboard__error">{error}</p>
        ) : (
          <div className="admin-dashboard__table-wrap">
            <table className="admin-dashboard__table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Chats</th>
                  <th>Total Tokens</th>
                  <th>Tokens (in / out)</th>
                  <th>Actual</th>
                  <th>Premium</th>
                  <th>Savings</th>
                  <th>Savings %</th>
                  <th>Top models</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="admin-dashboard__empty">
                      No users found
                    </td>
                  </tr>
                ) : (
                  rows.map((row) => (
                    <tr key={row.user_id}>
                      <td>{row.email}</td>
                      <td>{row.total_chats}</td>
                      <td>
                        {formatTokenTotal(row.total_input_tokens, row.total_output_tokens)}
                      </td>
                      <td>
                        {row.total_input_tokens.toLocaleString()} /{" "}
                        {row.total_output_tokens.toLocaleString()}
                      </td>
                      <td>
                        <div className="admin-cost-cell">
                          <span>{formatUsd(row.actual_cost)}</span>
                        </div>
                      </td>
                      <td>
                        <div className="admin-cost-cell">
                          <span>{formatUsd(row.premium_baseline_cost)}</span>
                        </div>
                      </td>
                      <td>{formatUsd(row.savings)}</td>
                      <td>{row.savings_percentage}%</td>
                      <td>
                        {row.most_used_models?.length
                          ? row.most_used_models.join(", ")
                          : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="admin-dashboard__section panel">
        <div className="admin-dashboard__section-header">
          <div>
            <h3 className="admin-dashboard__section-title">User Usage Metrics</h3>
            <p className="admin-dashboard__section-subtitle">
              Prompt volume, sessions, models, features, and query categories per user.
            </p>
          </div>
          <button
            type="button"
            className="documents-refresh"
            onClick={loadMetrics}
            disabled={metricsLoading}
          >
            {metricsLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        <div className="admin-metrics-filters">
          <label>
            Start date
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) =>
                setFilters((f) => ({ ...f, startDate: e.target.value }))
              }
            />
          </label>
          <label>
            End date
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) =>
                setFilters((f) => ({ ...f, endDate: e.target.value }))
              }
            />
          </label>
          <label>
            Granularity
            <select
              value={filters.granularity}
              onChange={(e) =>
                setFilters((f) => ({ ...f, granularity: e.target.value }))
              }
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>
          <button type="button" className="api-keys-form__submit" onClick={loadMetrics}>
            Apply
          </button>
        </div>

        {metricsError && <div className="alert alert--error">{metricsError}</div>}

        {metricsLoading ? (
          <p className="admin-dashboard__status">Loading user metrics…</p>
        ) : (
          <div className="admin-dashboard__table-wrap">
            <table className="admin-dashboard__table admin-metrics-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Prompts</th>
                  <th>Avg / session</th>
                  <th>Top model</th>
                  <th>Top category</th>
                  <th>Avg latency</th>
                  <th>Tokens</th>
                  <th>Actual</th>
                  <th>Savings</th>
                </tr>
              </thead>
              <tbody>
                {metrics.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="admin-dashboard__empty">
                      No metrics for this filter
                    </td>
                  </tr>
                ) : (
                  metrics.map((row) => (
                    <UserMetricsRow
                      key={row.user_id}
                      row={row}
                      expanded={expandedUserId === row.user_id}
                      onToggle={() =>
                        setExpandedUserId((current) =>
                          current === row.user_id ? null : row.user_id
                        )
                      }
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
