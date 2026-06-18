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
  fetchProviderUsage,
  fetchSummary,
} from "../api/analytics.js";
import { InlineCostTokens } from "./CostMetricDisplay.jsx";
import { downloadAnalyticsReport } from "../utils/exportAnalyticsReport.js";
import { formatCost, formatTokenTotal, savingsUsd } from "../utils/costMetrics.js";

function truncate(text, max = 180) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}…` : text;
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

function AnalyticsDashboard({ onRefresh }) {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [modelUsage, setModelUsage] = useState([]);
  const [providerUsage, setProviderUsage] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, historyData, usageData, providerData] = await Promise.all([
        fetchSummary(),
        fetchHistory(25),
        fetchModelUsage(),
        fetchProviderUsage(),
      ]);
      setSummary(summaryData);
      setHistory(historyData);
      setModelUsage(usageData);
      setProviderUsage(Array.isArray(providerData) ? providerData : []);
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
  const totalProviderRuns = providerUsage.reduce((sum, row) => sum + row.run_count, 0);

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
          <section className="analytics-kpis" aria-label="Summary metrics">
            <div className="analytics-kpi">
              <span className="analytics-kpi__label">Total Chats</span>
              <span className="analytics-kpi__value">{summary.total_chats}</span>
            </div>
            <div className="analytics-kpi">
              <span className="analytics-kpi__label">Actual</span>
              <span className="analytics-kpi__value">{formatCost(summary.total_cost)}</span>
              <span className="analytics-kpi__sub">
                {formatTokenTotal(summary.total_input_tokens, summary.total_output_tokens)}
              </span>
            </div>
            <div className="analytics-kpi analytics-kpi--premium">
              <span className="analytics-kpi__label">Premium</span>
              <span className="analytics-kpi__value">
                {formatCost(summary.premium_baseline_cost)}
              </span>
              <span className="analytics-kpi__sub">
                {formatTokenTotal(summary.total_input_tokens, summary.total_output_tokens)}
              </span>
            </div>
            <div className="analytics-kpi analytics-kpi--savings">
              <span className="analytics-kpi__label">Total Savings</span>
              <span className="analytics-kpi__value analytics-kpi__value--green">
                {formatCost(summary.total_savings)}
              </span>
              <span className="analytics-kpi__sub analytics-kpi__sub--savings">
                {summary.savings_percentage.toFixed(1)}%
              </span>
            </div>
            <div className="analytics-kpi">
              <span className="analytics-kpi__label">Total Tokens</span>
              <span className="analytics-kpi__value">
                {(summary.total_tokens ?? 0).toLocaleString()}
              </span>
              <span className="analytics-kpi__sub">
                Avg {(summary.avg_tokens_per_request ?? 0).toLocaleString()} / request
              </span>
            </div>
          </section>

          <section className="analytics-panel panel analytics-provider-panel">
            <h3 className="analytics-panel__title">Provider Usage Breakdown</h3>
            <div className="analytics-panel__scroll">
              {providerUsage.length === 0 ? (
                <p className="analytics-empty">
                  No provider usage yet. Send a chat to populate analytics.
                </p>
              ) : (
                <div className="analytics-table-wrap">
                  <table className="analytics-table analytics-provider-table">
                    <thead>
                      <tr>
                        <th>Provider</th>
                        <th>Runs</th>
                        <th>Share</th>
                        <th>Models</th>
                        <th>Cost</th>
                        <th>Tokens</th>
                        <th>Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {providerUsage.map((row) => {
                        const share =
                          totalProviderRuns > 0
                            ? ((row.run_count / totalProviderRuns) * 100).toFixed(1)
                            : "0.0";
                        const latencyMs = Number(row.average_latency_ms);
                        return (
                          <tr key={row.provider}>
                            <td>
                              <span
                                className={`provider-badge provider-badge--${row.provider}`}
                              >
                                {providerLabel(row.provider)}
                              </span>
                            </td>
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
                            <td>{row.model_count}</td>
                            <td>{formatCost(row.total_cost)}</td>
                            <td>{(row.total_tokens ?? 0).toLocaleString()}</td>
                            <td>
                              {Number.isFinite(latencyMs)
                                ? `${latencyMs.toFixed(0)} ms`
                                : "N/A"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>

          <div className="analytics-split">
            <section className="analytics-panel panel">
              <h3 className="analytics-panel__title">Model Usage Breakdown</h3>
              <div className="analytics-panel__scroll">
                {modelUsage.length === 0 ? (
                  <p className="analytics-empty">
                    No model runs yet. Send a chat to populate analytics.
                  </p>
                ) : (
                  <div className="analytics-table-wrap">
                    <table className="analytics-table">
                      <thead>
                        <tr>
                          <th>Model</th>
                          <th>Runs</th>
                          <th>Share</th>
                          <th>Cost</th>
                          <th>Total Tokens</th>
                          <th>Avg / Req</th>
                          <th>Latency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {modelUsage.map((row) => {
                          const share =
                            totalRuns > 0
                              ? ((row.run_count / totalRuns) * 100).toFixed(1)
                              : "0.0";
                          const latencyMs = Number(row.average_latency_ms);
                          return (
                            <tr key={row.model}>
                              <td className="analytics-table__model">
                                <span
                                  className={`provider-badge provider-badge--${row.provider || "groq"}`}
                                >
                                  {providerLabel(row.provider || "groq")}
                                </span>
                                <span className="analytics-table__model-id">{row.model}</span>
                              </td>
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
                              <td>{(row.total_tokens ?? 0).toLocaleString()}</td>
                              <td>{(row.avg_tokens_per_request ?? 0).toLocaleString()}</td>
                              <td>
                                {Number.isFinite(latencyMs)
                                  ? `${latencyMs.toFixed(0)} ms`
                                  : "N/A"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>

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
                          <InlineCostTokens
                            label="Actual"
                            cost={row.actual_cost}
                            inputTokens={row.input_tokens}
                            outputTokens={row.output_tokens}
                          />
                          <InlineCostTokens
                            label="Premium"
                            cost={row.premium_cost}
                            inputTokens={row.input_tokens}
                            outputTokens={row.output_tokens}
                          />
                          <span className="analytics-conv__saved">
                            Saved {formatCost(savingsUsd(row.actual_cost, row.premium_cost))} (
                            {row.savings_percentage.toFixed(1)}%)
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
