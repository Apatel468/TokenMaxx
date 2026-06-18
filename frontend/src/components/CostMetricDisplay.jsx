/**
 * Reusable cost + token metric block (routing panel, analytics, etc.).
 */
import {
  formatCost,
  formatTokenBreakdown,
  formatTokenTotal,
  savingsUsd,
} from "../utils/costMetrics.js";

export function CostMetricCard({
  label,
  cost,
  inputTokens,
  outputTokens,
  variant = "",
  showBreakdown = true,
}) {
  const breakdown = showBreakdown
    ? formatTokenBreakdown(inputTokens, outputTokens)
    : null;

  return (
    <div className={`cost-card ${variant}`.trim()}>
      <span className="cost-card__label">{label}</span>
      <span className="cost-card__value">{formatCost(cost)}</span>
      <span className="cost-card__sub">{formatTokenTotal(inputTokens, outputTokens)}</span>
      {breakdown && (
        <span className="cost-card__detail">
          Input: {breakdown.input}
          <br />
          Output: {breakdown.output}
        </span>
      )}
    </div>
  );
}

export function SavingsMetricCard({
  label = "Saved",
  actualCost,
  premiumCost,
  savingsPercentage,
  inputTokens,
  outputTokens,
  compact = false,
}) {
  const saved = savingsUsd(actualCost, premiumCost);
  const pct = Number(savingsPercentage) || 0;

  if (compact) {
    return (
      <div className="cost-card cost-card--savings">
        <span className="cost-card__label">{label}</span>
        <span className="cost-card__value cost-card__value--savings">
          {formatCost(saved)}
          <span className="cost-card__savings-pct"> ({pct.toFixed(1)}%)</span>
        </span>
        <span className="cost-card__sub">{formatTokenTotal(inputTokens, outputTokens)}</span>
      </div>
    );
  }

  return (
    <div className="cost-card cost-card--savings">
      <span className="cost-card__label">Savings</span>
      <span className="cost-card__value cost-card__value--savings">
        {pct.toFixed(1)}%
      </span>
      <span className="cost-card__sub cost-card__sub--savings">
        Saved {formatCost(saved)}
      </span>
      <span className="cost-card__sub">{formatTokenTotal(inputTokens, outputTokens)}</span>
    </div>
  );
}

export function InlineCostTokens({
  label,
  cost,
  inputTokens,
  outputTokens,
  className = "",
}) {
  return (
    <span className={`inline-cost-tokens ${className}`.trim()}>
      <span className="inline-cost-tokens__label">{label}</span>{" "}
      <span className="inline-cost-tokens__cost">{formatCost(cost)}</span>
      <span className="inline-cost-tokens__tokens">
        {formatTokenTotal(inputTokens, outputTokens)}
      </span>
    </span>
  );
}
