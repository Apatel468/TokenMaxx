/**
 * Build and download a TokenMaxx analytics CSV from dashboard state.
 */

function escapeCsvField(value) {
  const text = value == null ? "" : String(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function csvRow(fields) {
  return fields.map(escapeCsvField).join(",");
}

function formatCostPlain(value) {
  return Number(value).toFixed(6);
}

/**
 * @param {object} summary — GET /analytics/summary
 * @param {Array} modelUsage — GET /analytics/model-usage
 * @param {Array} history — GET /analytics/history
 */
export function buildAnalyticsCsv(summary, modelUsage, history) {
  const lines = [];
  const totalRuns = modelUsage.reduce((sum, row) => sum + row.run_count, 0);
  const generatedAt = new Date().toLocaleString();

  lines.push("TokenMaxx Analytics Report");
  lines.push(`Generated,${escapeCsvField(generatedAt)}`);
  lines.push("");

  lines.push("Summary");
  lines.push(csvRow(["Metric", "Value"]));
  lines.push(csvRow(["Total Chats", summary.total_chats]));
  lines.push(csvRow(["Actual Cost", formatCostPlain(summary.total_cost)]));
  lines.push(
    csvRow(["Premium Cost", formatCostPlain(summary.premium_baseline_cost)])
  );
  lines.push(csvRow(["Total Savings", formatCostPlain(summary.total_savings)]));
  lines.push(
    csvRow(["Savings Percentage", `${summary.savings_percentage.toFixed(1)}%`])
  );
  lines.push("");

  lines.push("Model Usage Breakdown");
  lines.push(
    csvRow([
      "Model",
      "Runs",
      "Share %",
      "Total Cost",
      "Average Latency (ms)",
    ])
  );
  for (const row of modelUsage) {
    const share =
      totalRuns > 0
        ? ((row.run_count / totalRuns) * 100).toFixed(1)
        : "0.0";
    lines.push(
      csvRow([
        row.model,
        row.run_count,
        share,
        formatCostPlain(row.total_cost),
        row.average_latency_ms.toFixed(0),
      ])
    );
  }
  lines.push("");

  lines.push("Recent Conversations");
  lines.push(
    csvRow([
      "ID",
      "Timestamp",
      "Task Type",
      "Selected Model",
      "Prompt",
      "Response",
      "Actual Cost",
      "Premium Cost",
      "Savings %",
    ])
  );
  for (const row of history) {
    lines.push(
      csvRow([
        row.id,
        row.timestamp,
        row.task_type,
        row.selected_model,
        row.prompt,
        row.response,
        formatCostPlain(row.actual_cost),
        formatCostPlain(row.premium_cost),
        row.savings_percentage.toFixed(1),
      ])
    );
  }

  return `${lines.join("\n")}\n`;
}

const REPORT_FILENAME = "tokenmaxx-analytics-report.csv";

/**
 * Trigger a browser download of the analytics CSV report.
 */
export function downloadAnalyticsReport(summary, modelUsage, history) {
  const csv = buildAnalyticsCsv(summary, modelUsage, history);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = REPORT_FILENAME;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
