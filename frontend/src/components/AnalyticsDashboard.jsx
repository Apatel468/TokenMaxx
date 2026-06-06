/**
 * AnalyticsDashboard — shows SQLite stats from the backend.
 *
 * Fetches three endpoints on load:
 *   GET /analytics/summary
 *   GET /analytics/history
 *   GET /analytics/model-usage
 */
import { useEffect, useState } from "react";
import {
  fetchHistory,
  fetchModelUsage,
  fetchSummary,
} from "../api/analytics.js";

function formatCost(value) {
  return `$${Number(value).toFixed(6)}`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString();
}

function AnalyticsDashboard({ onRefresh }) {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [modelUsage, setModelUsage] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /** Load all analytics data from the backend */
  async function loadAnalytics() {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, historyData, usageData] = await Promise.all([
        fetchSummary(),
        fetchHistory(20),
        fetchModelUsage(),
      ]);
      setSummary(summaryData);
      setHistory(historyData);
      setModelUsage(usageData);
    } catch (err) {
      setError(
        err.message ||
          "Could not load analytics. Is the backend running on port 8001?"
      );
    } finally {
      setLoading(false);
    }
  }

  // Fetch on mount; re-fetch when parent bumps refreshKey
  useEffect(() => {
    loadAnalytics();
  }, [onRefresh]);

  if (loading) {
    return (
      <div className="analytics-page">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading analytics…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-page">
        <div className="alert alert--error">{error}</div>
        <button type="button" className="prompt-form__submit" onClick={loadAnalytics}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      <div className="analytics-header">
        <h2 className="panel__title">Analytics Dashboard</h2>
        <button type="button" className="analytics-refresh" onClick={loadAnalytics}>
          Refresh
        </button>
      </div>

      {/* Summary stat cards */}
      <div className="analytics-summary-grid">
        <div className="stat-card">
          <span className="stat-card__label">Total Chats</span>
          <span className="stat-card__value">{summary.total_chats}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">Total Cost</span>
          <span className="stat-card__value">{formatCost(summary.total_cost)}</span>
        </div>
        <div className="stat-card cost-card--premium">
          <span className="stat-card__label">Premium Baseline</span>
          <span className="stat-card__value">
            {formatCost(summary.premium_baseline_cost)}
          </span>
        </div>
        <div className="stat-card cost-card--savings">
          <span className="stat-card__label">Total Savings</span>
          <span className="stat-card__value cost-card__value--savings">
            {formatCost(summary.total_savings)}
          </span>
        </div>
        <div className="stat-card cost-card--savings">
          <span className="stat-card__label">Savings %</span>
          <span className="stat-card__value cost-card__value--savings">
            {summary.savings_percentage.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Model usage table */}
      <section className="panel">
        <h3 className="panel__title">Model Usage</h3>
        {modelUsage.length === 0 ? (
          <p className="panel__hint">No model runs yet. Submit a chat prompt first.</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Runs</th>
                  <th>Input Tokens</th>
                  <th>Output Tokens</th>
                  <th>Total Cost</th>
                  <th>Avg Latency</th>
                </tr>
              </thead>
              <tbody>
                {modelUsage.map((row) => (
                  <tr key={row.model}>
                    <td>{row.model}</td>
                    <td>{row.run_count}</td>
                    <td>{row.total_input_tokens.toLocaleString()}</td>
                    <td>{row.total_output_tokens.toLocaleString()}</td>
                    <td>{formatCost(row.total_cost)}</td>
                    <td>{row.average_latency_ms.toFixed(0)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Chat history table */}
      <section className="panel">
        <h3 className="panel__title">Chat History</h3>
        {history.length === 0 ? (
          <p className="panel__hint">No chat history yet.</p>
        ) : (
          <div className="history-list">
            {history.map((row) => (
              <div key={row.id} className="history-item">
                <div className="history-item__meta">
                  <span className="task-badge">{row.task_type}</span>
                  <span className="history-item__model">{row.selected_model}</span>
                  <span className="history-item__time">{formatDate(row.timestamp)}</span>
                </div>
                <p className="history-item__prompt">
                  <strong>Prompt:</strong> {row.prompt}
                </p>
                <p className="history-item__response">
                  <strong>Response:</strong>{" "}
                  {row.response.length > 200
                    ? `${row.response.slice(0, 200)}…`
                    : row.response}
                </p>
                <div className="history-item__costs">
                  <span>Actual: {formatCost(row.actual_cost)}</span>
                  <span>Premium: {formatCost(row.premium_cost)}</span>
                  <span className="cost-card__value--savings">
                    Saved: {row.savings_percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default AnalyticsDashboard;
