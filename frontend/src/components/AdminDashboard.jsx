/**
 * AdminDashboard — employee usage metrics (admin role only).
 *
 * Shows per-user chats, tokens, costs, savings, and top models.
 */
import { useEffect, useState } from "react";
import { fetchEmployeeUsage } from "../api/admin.js";

function formatUsd(value) {
  return `$${Number(value).toFixed(4)}`;
}

export default function AdminDashboard() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchEmployeeUsage();
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load admin metrics");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="admin-dashboard__status">Loading employee metrics…</p>;
  }

  if (error) {
    return <p className="admin-dashboard__error">{error}</p>;
  }

  return (
    <div className="admin-dashboard">
      <header className="admin-dashboard__header">
        <h2>Employee usage</h2>
        <p>Organization-wide chat cost and model usage per user.</p>
      </header>

      <div className="admin-dashboard__table-wrap">
        <table className="admin-dashboard__table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Chats</th>
              <th>Tokens (in / out)</th>
              <th>Actual cost</th>
              <th>Premium baseline</th>
              <th>Savings</th>
              <th>Savings %</th>
              <th>Top models</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={8} className="admin-dashboard__empty">
                  No users found
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.user_id}>
                  <td>{row.email}</td>
                  <td>{row.total_chats}</td>
                  <td>
                    {row.total_input_tokens.toLocaleString()} /{" "}
                    {row.total_output_tokens.toLocaleString()}
                  </td>
                  <td>{formatUsd(row.actual_cost)}</td>
                  <td>{formatUsd(row.premium_baseline_cost)}</td>
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
    </div>
  );
}
