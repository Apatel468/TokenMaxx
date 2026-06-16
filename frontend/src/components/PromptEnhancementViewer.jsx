/**
 * PromptEnhancementViewer — collapsible Prompt Intelligence v2 details.
 *
 * Rendered below assistant replies. Collapsed by default.
 */
import { useState } from "react";

function displayEnhancedPrompt(enhancedPrompt, originalPrompt, promptAnalysis) {
  const fromAnalysis = promptAnalysis?.enhanced_prompt?.trim();
  if (fromAnalysis) return fromAnalysis;

  const text = (enhancedPrompt || "").trim();
  if (!text) return (originalPrompt || "").trim();

  return text
    .replace(
      /\n\n\[Original user request — preserve this intent:[\s\S]*?\]\s*$/i,
      "",
    )
    .replace(/^User request \(preserve this intent exactly\):\s*/i, "")
    .trim();
}

function PromptEnhancementViewer({
  originalPrompt,
  enhancedPrompt,
  enhancementMethod = "",
  promptAnalysis = null,
}) {
  const [open, setOpen] = useState(false);

  const original = (originalPrompt || promptAnalysis?.original_prompt || "").trim();
  const enhanced = displayEnhancedPrompt(
    enhancedPrompt,
    originalPrompt,
    promptAnalysis,
  );

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

  const taskType = promptAnalysis?.task_type;
  const complexityLevel = promptAnalysis?.complexity_level;
  const persona = promptAnalysis?.persona;
  const strategy = promptAnalysis?.enhancement_strategy;

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

          {unchanged && !promptAnalysis && (
            <p className="prompt-enhancement__note">
              Original and enhanced prompts are identical for this turn.
            </p>
          )}

          {(taskType || complexityLevel || persona || strategy) && (
            <div className="prompt-enhancement__meta">
              {taskType && (
                <div className="prompt-enhancement__meta-item">
                  <span className="prompt-enhancement__label">Task Type</span>
                  <span className="task-badge">{taskType}</span>
                </div>
              )}
              {complexityLevel && (
                <div className="prompt-enhancement__meta-item">
                  <span className="prompt-enhancement__label">
                    Complexity Level
                  </span>
                  <span className="prompt-enhancement__meta-value">
                    {complexityLevel}
                    {promptAnalysis?.complexity_score != null &&
                      ` (${promptAnalysis.complexity_score}/100)`}
                  </span>
                </div>
              )}
              {persona && (
                <div className="prompt-enhancement__meta-item">
                  <span className="prompt-enhancement__label">Persona</span>
                  <span className="prompt-enhancement__meta-value">{persona}</span>
                </div>
              )}
              {strategy && (
                <div className="prompt-enhancement__meta-item">
                  <span className="prompt-enhancement__label">
                    Enhancement Strategy
                  </span>
                  <span className="prompt-enhancement__meta-value">
                    {strategy.replaceAll("_", " ")}
                  </span>
                </div>
              )}
            </div>
          )}

          <div className="prompt-enhancement__section">
            <span className="prompt-enhancement__label">Original Prompt</span>
            <pre className="prompt-enhancement__text">{original || "—"}</pre>
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
