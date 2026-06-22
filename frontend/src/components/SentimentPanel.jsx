/**
 * SentimentPanel — real-time sentiment for the latest user message + conversation trend.
 */

export const SENTIMENT_LABELS = [
  "positive",
  "neutral",
  "negative",
  "excited",
  "frustrated",
  "confused",
  "urgent",
];

const SENTIMENT_ICONS = {
  positive: "😊",
  neutral: "😐",
  negative: "😞",
  excited: "🎉",
  frustrated: "😤",
  confused: "🤔",
  urgent: "⚡",
  unknown: "❓",
};

export function formatSentimentLabel(label) {
  if (!label || label === "unknown") return "Unknown";
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function sentimentBadgeClass(label) {
  const safe = (label || "unknown").toLowerCase();
  return `sentiment-badge sentiment-badge--${safe}`;
}

/** Map 0–100 confidence score to a readable tier label. */
export function confidenceLabel(confidence) {
  const value = Number(confidence) || 0;
  if (value < 50) return "Low confidence";
  if (value < 75) return "Mid confidence";
  return "Very confident";
}

export function confidenceTierClass(confidence) {
  const value = Number(confidence) || 0;
  if (value < 50) return "sentiment-confidence--low";
  if (value < 75) return "sentiment-confidence--mid";
  return "sentiment-confidence--high";
}

function SentimentTrendBar({ items }) {
  if (!items?.length) return null;

  return (
    <div className="sentiment-trend" aria-label="Sentiment trend across conversation">
      <span className="sentiment-trend__label">Trend</span>
      <div className="sentiment-trend__track">
        {items.map((item, index) => (
          <span
            key={`${item.message_id || "pending"}-${index}`}
            className={`sentiment-trend__dot sentiment-trend__dot--${(item.label || "unknown").toLowerCase()}`}
            title={`${formatSentimentLabel(item.label)} — ${confidenceLabel(item.confidence)}`}
          />
        ))}
      </div>
    </div>
  );
}

function SentimentHistoryList({ items }) {
  if (!items?.length) return null;

  const recent = items.slice(-6).reverse();

  return (
    <ul className="sentiment-history">
      {recent.map((item, index) => (
        <li key={`${item.message_id || "row"}-${index}`} className="sentiment-history__item">
          <span className={sentimentBadgeClass(item.label)}>
            <span className="sentiment-badge__icon" aria-hidden="true">
              {SENTIMENT_ICONS[item.label] || SENTIMENT_ICONS.unknown}
            </span>
            {formatSentimentLabel(item.label)}
          </span>
          <span
            className={`sentiment-history__confidence ${confidenceTierClass(item.confidence)}`}
          >
            {confidenceLabel(item.confidence)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function SentimentPanel({
  current = null,
  history = [],
  loading = false,
  error = null,
}) {
  const display = current || null;
  const isUnknown = !display || display.label === "unknown" || error;
  const label = isUnknown && error ? "unknown" : display?.label || "neutral";
  const confidence = isUnknown && error ? 0 : display?.confidence ?? 0;
  const explanation =
    isUnknown && error
      ? "Unable to determine sentiment"
      : display?.explanation || "Send a message to analyze tone.";

  return (
    <section
      className="panel sentiment-panel"
      aria-live="polite"
      aria-busy={loading}
    >
      <h2 className="panel__title sentiment-panel__title">Sentiment Analysis</h2>

      <div className="sentiment-panel__body">
        {!display && !loading && !error && (
          <div className="empty-state empty-state--compact">
            <p>Your message tone will appear here before the model replies.</p>
          </div>
        )}

        {loading && (
          <div className="sentiment-panel__loading" role="status">
            <span className="sentiment-spinner" aria-hidden="true" />
            Analyzing tone…
          </div>
        )}

        {(display || error) && !loading && (
          <div className="sentiment-panel__current">
            <div className="sentiment-panel__header">
              <span className={sentimentBadgeClass(label)}>
                <span className="sentiment-badge__icon" aria-hidden="true">
                  {SENTIMENT_ICONS[label] || SENTIMENT_ICONS.unknown}
                </span>
                {formatSentimentLabel(label)}
              </span>
              <span
                className={`sentiment-panel__confidence ${confidenceTierClass(confidence)}`}
              >
                {confidenceLabel(confidence)}
              </span>
            </div>

            <p className="sentiment-panel__explanation">{explanation}</p>

            <SentimentTrendBar items={history} />
          </div>
        )}

        {history.length > 0 && (
          <div className="sentiment-panel__history">
            <h3 className="sentiment-panel__history-title">Recent messages</h3>
            <SentimentHistoryList items={history} />
          </div>
        )}
      </div>
    </section>
  );
}
