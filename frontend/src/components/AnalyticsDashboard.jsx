/**
 * Analytics Dashboard — live stats from backend SQLite via REST API.
 *
 * Data sources (no hardcoded numbers):
 *   GET /analytics/summary      → KPI cards
 *   GET /analytics/model-usage  → model breakdown table
 *   GET /analytics/history      → recent conversations
 */
import { useCallback, useEffect, useState } from "react";
import {
  fetchHistory,
  fetchModelUsage,
  fetchSummary,
} from "../api/analytics.js";
import { downloadAnalyticsReport } from "../utils/exportAnalyticsReport.js";

function formatCost(value) {
  return `$${Number(value).toFixed(6)}`;
}

function truncate(text, max = 180) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

function AnalyticsDashboard({ onRefresh }) {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [modelUsage, setModelUsage] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, historyData, usageData] = await Promise.all([
        fetchSummary(),
        fetchHistory(25),
        fetchModelUsage(),
      ]);
      setSummary(summaryData);
      setHistory(historyData);
      setModelUsage(usageData);
    } catch (err) {
      setError(
        err.message ||
          "Could not load analytics. Check VITE_API_BASE and that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics, onRefresh]);

  const totalRuns = modelUsage.reduce((sum, row) => sum + row.run_count, 0);

  const handleExportReport = () => {
    if (!summary) return;
    downloadAnalyticsReport(summary, modelUsage, history);
  };

  return (
    <div className="analytics-page">
      <header className="analytics-header">
        <div>
          <h2 className="analytics-header__title">TokenMaxx Analytics</h2>
          <p className="analytics-header__subtitle">
            Maximum Intelligence, Minimum Cost — live usage and savings
          </p>
        </div>
        <div className="analytics-header__actions">
          <button
            type="button"
            className="analytics-export"
            onClick={handleExportReport}
            disabled={loading || !summary}
          >
            Export Report
          </button>
          <button
            type="button"
            className="analytics-refresh"
            onClick={loadAnalytics}
            disabled={loading}
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      {error && (
        <div className="alert alert--error analytics-error">{error}</div>
      )}

      {loading && !summary ? (
        <div className="analytics-loading">
          <div className="spinner" />
          <p>Loading analytics…</p>
        </div>
      ) : summary ? (
        <>
          {/* KPI row — all values from GET /analytics/summary */}
          <section className="analytics-kpis" aria-label="Summary metrics">
            <div className="analytics-kpi">
              <span className="analytics-kpi__label">Total Chats</span>
              <span className="analytics-kpi__value">{summary.total_chats}</span>
            </div>
            <div className="analytics-kpi">
              <span className="analytics-kpi__label">Actual Cost</span>
              <span className="analytics-kpi__value">
                {formatCost(summary.total_cost)}
              </span>
            </div>
            <div className="analytics-kpi analytics-kpi--premium">
              <span className="analytics-kpi__label">Premium Cost</span>
              <span className="analytics-kpi__value">
                {formatCost(summary.premium_baseline_cost)}
              </span>
            </div>
            <div className="analytics-kpi analytics-kpi--savings">
              <span className="analytics-kpi__label">Total Savings</span>
              <span className="analytics-kpi__value analytics-kpi__value--green">
                {formatCost(summary.total_savings)}
              </span>
            </div>
            <div className="analytics-kpi analytics-kpi--savings">
              <span className="analytics-kpi__label">Savings %</span>
              <span className="analytics-kpi__value analytics-kpi__value--green">
                {summary.savings_percentage.toFixed(1)}%
              </span>
            </div>
          </section>

          <div className="analytics-split">
            {/* Model usage — GET /analytics/model-usage */}
            <section className="analytics-panel panel">
              <h3 className="analytics-panel__title">Model Usage Breakdown</h3>
              <div className="analytics-panel__scroll">
                {modelUsage.length === 0 ? (
                  <p className="analytics-empty">
                    No model runs yet. Send a chat to populate analytics.
                  </p>
                ) : (
                  <table className="analytics-table">
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Runs</th>
                        <th>Share</th>
                        <th>Cost</th>
                        <th>Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelUsage.map((row) => {
                        const share =
                          totalRuns > 0
                            ? ((row.run_count / totalRuns) * 100).toFixed(1)
                            : "0.0";
                        return (
                          <tr key={row.model}>
                            <td className="analytics-table__model">{row.model}</td>
                            <td>{row.run_count}</td>
                            <td>
                              <div className="analytics-bar">
                                <div
                                  className="analytics-bar__fill"
                                  style={{ width: `${share}%` }}
                                />
                                <span className="analytics-bar__label">{share}%</span>
                              </div>
                            </td>
                            <td>{formatCost(row.total_cost)}</td>
                            <td>{row.average_latency_ms.toFixed(0)} ms</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            </section>

            {/* Recent conversations — GET /analytics/history */}
            <section className="analytics-panel panel">
              <h3 className="analytics-panel__title">Recent Conversations</h3>
              <div className="analytics-panel__scroll">
                {history.length === 0 ? (
                  <p className="analytics-empty">
                    No conversations recorded yet. Start a chat in TokenMaxx to see analytics here.
                  </p>
                ) : (
                  <ul className="analytics-conversations">
                    {history.map((row) => (
                      <li key={row.id} className="analytics-conv">
                        <div className="analytics-conv__top">
                          <span className="task-badge">{row.task_type}</span>
                          <span className="analytics-conv__model">
                            {row.selected_model}
                          </span>
                          <time className="analytics-conv__time">
                            {row.timestamp}
                          </time>
                        </div>
                        <p className="analytics-conv__prompt">
                          {truncate(row.prompt)}
                        </p>
                        <p className="analytics-conv__response">
                          {truncate(row.response)}
                        </p>
                        <div className="analytics-conv__costs">
                          <span>Actual {formatCost(row.actual_cost)}</span>
                          <span>Premium {formatCost(row.premium_cost)}</span>
                          <span className="analytics-conv__saved">
                            Saved {row.savings_percentage.toFixed(1)}%
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}

export default AnalyticsDashboard;
