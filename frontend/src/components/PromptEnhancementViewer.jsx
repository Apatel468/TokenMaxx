/**
 * PromptEnhancementViewer — collapsible original vs enhanced prompt comparison.
 *
 * Rendered below assistant replies. Collapsed by default; user expands to inspect
 * how TokenMaxx optimized the prompt before routing.
 */
import { useState } from "react";

/** Strip internal backend suffixes from older enhanced prompts. */
function displayEnhancedPrompt(enhancedPrompt, originalPrompt) {
  const text = (enhancedPrompt || "").trim();
  if (!text) return (originalPrompt || "").trim();

  return text
    .replace(
      /\n\n\[Original user request — preserve this intent:[\s\S]*?\]\s*$/i,
      "",
    )
    .trim();
}

function PromptEnhancementViewer({
  originalPrompt,
  enhancedPrompt,
  enhancementMethod = "",
}) {
  const [open, setOpen] = useState(false);

  const original = (originalPrompt || "").trim();
  const enhanced = displayEnhancedPrompt(enhancedPrompt, originalPrompt);

  if (!original && !enhanced) {
    return null;
  }

  const unchanged = original && enhanced && original === enhanced;
  const methodLabel =
    enhancementMethod === "disabled"
      ? "Enhancement off"
      : enhancementMethod === "reused"
        ? "Reused from original turn"
        : enhancementMethod === "ai"
          ? "AI optimized"
          : enhancementMethod === "rule_fallback"
            ? "Rule-based optimization"
            : "";

  return (
    <div className="prompt-enhancement">
      <button
        type="button"
        className="prompt-enhancement__toggle"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        <span className="prompt-enhancement__toggle-label">
          View Prompt Optimization
        </span>
        <span className="prompt-enhancement__chevron" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
      </button>

      {open && (
        <div className="prompt-enhancement__body">
          {methodLabel && (
            <span
              className={`enhancement-badge ${
                enhancementMethod === "disabled"
                  ? "enhancement-badge--off"
                  : "enhancement-badge--on"
              }`}
            >
              {methodLabel}
            </span>
          )}

          {unchanged && (
            <p className="prompt-enhancement__note">
              Original and enhanced prompts are identical for this turn.
            </p>
          )}

          <div className="prompt-enhancement__section">
            <span className="prompt-enhancement__label">Original Prompt</span>
            <pre className="prompt-enhancement__text">
              {original || "—"}
            </pre>
          </div>

          <div className="prompt-enhancement__section">
            <span className="prompt-enhancement__label">Enhanced Prompt</span>
            <pre className="prompt-enhancement__text">
              {enhanced || original || "—"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default PromptEnhancementViewer;
