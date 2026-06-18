/**
 * Shared helpers for cost + token display across TokenMaxx UI.
 */

export function formatCost(value) {
  if (value == null || Number.isNaN(Number(value))) return "N/A";
  return `$${Number(value).toFixed(6)}`;
}

export function formatCostShort(value) {
  if (value == null || Number.isNaN(Number(value))) return "N/A";
  return `$${Number(value).toFixed(4)}`;
}

export function hasTokenData(inputTokens, outputTokens) {
  const input = Number(inputTokens);
  const output = Number(outputTokens);
  return input > 0 || output > 0;
}

export function totalTokens(inputTokens, outputTokens) {
  if (!hasTokenData(inputTokens, outputTokens)) return null;
  return Number(inputTokens) + Number(outputTokens);
}

export function formatTokenTotal(inputTokens, outputTokens) {
  const total = totalTokens(inputTokens, outputTokens);
  if (total == null) return "N/A";
  return `${total.toLocaleString()} tokens`;
}

export function formatTokenBreakdown(inputTokens, outputTokens) {
  if (!hasTokenData(inputTokens, outputTokens)) return null;
  return {
    input: Number(inputTokens).toLocaleString(),
    output: Number(outputTokens).toLocaleString(),
    total: (Number(inputTokens) + Number(outputTokens)).toLocaleString(),
  };
}

export function savingsUsd(actualCost, premiumCost) {
  const actual = Number(actualCost) || 0;
  const premium = Number(premiumCost) || 0;
  return Math.max(premium - actual, 0);
}

export function formatSavingsUsd(actualCost, premiumCost) {
  return formatCost(savingsUsd(actualCost, premiumCost));
}
