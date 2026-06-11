"""
Model Scorer — ranks any number of Groq models for a task type.

Composite score (0–100):
  score = (task_match * 0.4) + (cost_efficiency * 0.2) + (speed_score * 0.2)
        + (reasoning_score * 0.2)

task_match is derived per task from registry capability scores (coding,
writing, reasoning) using weights in config/models.yaml → task_profiles.

To route a new Groq model: add metadata to model_registry.py only —
this module has no hardcoded model ids.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.model_registry import ModelMetadata
from services.config_loader import get_task_profile, resolve_task_key
from services.groq_models import GroqModelRecord

WEIGHT_TASK_MATCH = 0.4
WEIGHT_COST = 0.2
WEIGHT_SPEED = 0.2
WEIGHT_REASONING = 0.2


@dataclass
class CandidateScore:
    """Scored model candidate returned to the router and API."""

    model_id: str
    model_name: str
    score: float
    task_match: float
    cost_efficiency: float
    speed_score: float
    reasoning_score: float
    provider: str

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "score": round(self.score, 2),
            "task_match": round(self.task_match, 2),
            "cost_efficiency": round(self.cost_efficiency, 2),
            "speed_score": round(self.speed_score, 2),
            "reasoning_score": round(self.reasoning_score, 2),
            "provider": self.provider,
        }


def _blended_cost_per_1m(meta: ModelMetadata) -> float:
    rates = meta["cost_per_1m_tokens"]
    return rates["input"] + rates["output"]


def _compute_task_match(task_key: str, meta: ModelMetadata) -> float:
    """
    Weighted blend of coding / writing / reasoning scores for this task.

    Weights come from models.yaml task_profiles — not from model ids.
    """
    profile = get_task_profile(task_key)
    weights = profile.get(
        "task_match_weights",
        {"coding": 0.33, "reasoning": 0.34, "writing": 0.33},
    )
    coding_w = weights.get("coding", 0.33)
    reasoning_w = weights.get("reasoning", 0.34)
    writing_w = weights.get("writing", 0.33)

    total_w = coding_w + reasoning_w + writing_w
    if total_w <= 0:
        total_w = 1.0

    return (
        meta["coding_score"] * coding_w
        + meta["reasoning_score"] * reasoning_w
        + meta["writing_score"] * writing_w
    ) / total_w


def _normalize_inverse(values: list[float], value: float) -> float:
    """
    Map lower-is-better metrics (cost, latency) to 0–100 scores.

    Cheapest / fastest model → 100; most expensive / slowest → 0.
    """
    if not values:
        return 50.0
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return 75.0
    return 100.0 * (hi - value) / (hi - lo)


def score_candidates(
    task_type: str,
    candidates: list[GroqModelRecord],
) -> list[CandidateScore]:
    """
    Score every candidate model for the given task type.

    Returns candidates sorted by score descending (best first).
    """
    if not candidates:
        return []

    task_key = resolve_task_key(task_type)
    costs = [_blended_cost_per_1m(c.metadata) for c in candidates]
    latencies = [c.metadata["avg_latency_ms"] for c in candidates]

    scored: list[CandidateScore] = []
    for record, cost, latency in zip(candidates, costs, latencies):
        meta = record.metadata
        task_match = _compute_task_match(task_key, meta)
        cost_efficiency = _normalize_inverse(costs, cost)
        speed_score = _normalize_inverse(latencies, latency)
        reasoning_component = float(meta["reasoning_score"])

        composite = (
            task_match * WEIGHT_TASK_MATCH
            + cost_efficiency * WEIGHT_COST
            + speed_score * WEIGHT_SPEED
            + reasoning_component * WEIGHT_REASONING
        )

        scored.append(
            CandidateScore(
                model_id=record.model_id,
                model_name=meta["model_name"],
                score=round(composite, 2),
                task_match=round(task_match, 2),
                cost_efficiency=round(cost_efficiency, 2),
                speed_score=round(speed_score, 2),
                reasoning_score=reasoning_component,
                provider=meta["provider"],
            )
        )

    scored.sort(key=lambda c: c.score, reverse=True)
    return scored


def pick_best_model(
    task_type: str,
    candidates: list[GroqModelRecord],
) -> tuple[CandidateScore | None, list[CandidateScore]]:
    """
    Return (winner, all_scored_candidates).

    Winner is the highest-scoring candidate, or None if the list is empty.
    """
    scored = score_candidates(task_type, candidates)
    winner = scored[0] if scored else None
    return winner, scored
