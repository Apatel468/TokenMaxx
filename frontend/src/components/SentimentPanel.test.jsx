import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SentimentPanel, {
  confidenceLabel,
  formatSentimentLabel,
  sentimentBadgeClass,
} from "../components/SentimentPanel.jsx";

describe("formatSentimentLabel", () => {
  it("capitalizes known labels", () => {
    expect(formatSentimentLabel("frustrated")).toBe("Frustrated");
    expect(formatSentimentLabel("positive")).toBe("Positive");
  });

  it("maps unknown to Unknown", () => {
    expect(formatSentimentLabel("unknown")).toBe("Unknown");
  });
});

describe("sentimentBadgeClass", () => {
  it("returns modifier class for label", () => {
    expect(sentimentBadgeClass("urgent")).toBe(
      "sentiment-badge sentiment-badge--urgent",
    );
  });
});

describe("confidenceLabel", () => {
  it("maps score ranges to tier labels", () => {
    expect(confidenceLabel(0)).toBe("Very low confidence");
    expect(confidenceLabel(45)).toBe("Low confidence");
    expect(confidenceLabel(55)).toBe("Mid confidence");
    expect(confidenceLabel(67)).toBe("Moderate confidence");
    expect(confidenceLabel(79)).toBe("High confidence");
    expect(confidenceLabel(95)).toBe("Very high confidence");
  });
});

describe("SentimentPanel", () => {
  it("shows empty state when idle", () => {
    render(<SentimentPanel current={null} history={[]} loading={false} error={null} />);

    expect(
      screen.getByText(/your message tone will appear here/i),
    ).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<SentimentPanel current={null} history={[]} loading error={null} />);

    expect(screen.getByText(/analyzing tone/i)).toBeInTheDocument();
  });

  it("renders current sentiment with confidence and explanation", () => {
    render(
      <SentimentPanel
        current={{
          label: "excited",
          confidence: 82.5,
          explanation: "Matched cue wow — reads as excited.",
        }}
        history={[]}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("Excited")).toBeInTheDocument();
    expect(screen.getByText("Very confident")).toBeInTheDocument();
    expect(screen.getByText(/reads as excited/i)).toBeInTheDocument();
  });

  it("shows fallback when analysis fails", () => {
    render(
      <SentimentPanel
        current={null}
        history={[]}
        loading={false}
        error="Unable to determine sentiment"
      />,
    );

    expect(screen.getByText("Unable to determine sentiment")).toBeInTheDocument();
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText("Low confidence")).toBeInTheDocument();
  });

  it("renders sentiment history trend", () => {
    render(
      <SentimentPanel
        current={{
          label: "positive",
          confidence: 70,
          explanation: "Thanks detected.",
        }}
        history={[
          { label: "neutral", confidence: 55, message_id: 1 },
          { label: "positive", confidence: 70, message_id: 2 },
        ]}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByLabelText(/sentiment trend/i)).toBeInTheDocument();
    expect(screen.getByText("Recent messages")).toBeInTheDocument();
    expect(screen.getByText("Neutral")).toBeInTheDocument();
  });
});
