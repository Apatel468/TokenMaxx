"""
Model Scorer — ranks Groq models for a task type with complexity-aware weights.

Composite score blends task fit, quality, speed, cost, and task-specific bonuses.
Cheap/fast models are favored for simple prompts; capability dominates for complex ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.model_registry import ModelMetadata
from services.config_loader import get_task_profile, resolve_task_key
from services.groq_models import GroqModelRecord

# Task-specific preference bonuses (added to composite — steers routing per task).
TASK_MODEL_BONUSES: dict[str, dict[str, float]] = {
    "general_qa": {
        "llama-3.1-8b-instant": 14.0,
        "openai/gpt-oss-20b": 3.0,
    },
    "classification": {
        "llama-3.1-8b-instant": 14.0,
    },
    "coding": {
        "qwen/qwen3-32b": 16.0,
    },
    "math": {
        "qwen/qwen3-32b": 16.0,
    },
    "reasoning": {
        "openai/gpt-oss-120b": 14.0,
        "qwen/qwen3-32b": 5.0,
    },
    "writing": {
        "llama-3.3-70b-versatile": 12.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 10.0,
    },
    "summarization": {
        "llama-3.1-8b-instant": 10.0,
        "llama-3.3-70b-versatile": 9.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 8.0,
    },
    "report": {
        "llama-3.3-70b-versatile": 13.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 11.0,
    },
    "creative": {
        "llama-3.3-70b-versatile": 11.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 9.0,
    },
    "research": {
        "openai/gpt-oss-120b": 12.0,
        "llama-3.3-70b-versatile": 7.0,
    },
}

_COMPLEX_TASK_TYPES = frozenset(
    {"reasoning", "research", "math", "coding", "report", "creative", "writing"}
)

_COMPLEXITY_KEYWORDS = (
    "step by step",
    "prove",
    "analyze",
    "analysis",
    "debug",
    "implement",
    "architecture",
    "optimize",
    "refactor",
    "puzzle",
    "theorem",
    "proof",
)


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
    task_preference_bonus: float = 0.0
    complexity_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "score": round(self.score, 2),
            "task_match": round(self.task_match, 2),
            "cost_efficiency": round(self.cost_efficiency, 2),
            "speed_score": round(self.speed_score, 2),
            "reasoning_score": round(self.reasoning_score, 2),
            "task_preference_bonus": round(self.task_preference_bonus, 2),
            "complexity_score": round(self.complexity_score, 2),
            "provider": self.provider,
        }


def compute_complexity(
    prompt: str,
    task_type: str,
    *,
    estimated_input_tokens: int = 0,
) -> float:
    """
    Estimate prompt complexity from 0.0 (simple) to 1.0 (complex).

    Used to shift scoring weights toward quality on harder prompts.
    """
    text = (prompt or "").strip().lower()
    token_est = estimated_input_tokens or max(len(text) // 4, 1)

    length_factor = min(token_est / 800.0, 1.0)
    task_factor = 0.28 if task_type in _COMPLEX_TASK_TYPES else 0.0
    structure_bonus = 0.12 if len(text) > 400 else 0.0

    if any(keyword in text for keyword in _COMPLEXITY_KEYWORDS):
        structure_bonus += 0.12

    return min(length_factor * 0.5 + task_factor + structure_bonus, 1.0)


def _score_weights(complexity: float) -> dict[str, float]:
    """Dynamic weights — cost/speed matter more for simple prompts."""
    if complexity < 0.35:
        return {
            "task": 0.42,
            "cost": 0.12,
            "speed": 0.16,
            "reasoning": 0.12,
        }
    if complexity > 0.65:
        return {
            "task": 0.50,
            "cost": 0.04,
            "speed": 0.08,
            "reasoning": 0.30,
        }
    return {
        "task": 0.46,
        "cost": 0.08,
        "speed": 0.12,
        "reasoning": 0.22,
    }


def _task_preference_bonus(task_type: str, model_id: str) -> float:
    return TASK_MODEL_BONUSES.get(task_type, {}).get(model_id, 0.0)


def _blended_cost_per_1m(meta: ModelMetadata) -> float:
    rates = meta["cost_per_1m_tokens"]
    return rates["input"] + rates["output"]


def _compute_task_match(task_key: str, meta: ModelMetadata) -> float:
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
    *,
    prompt: str = "",
    estimated_input_tokens: int = 0,
) -> list[CandidateScore]:
    """
    Score every candidate model for the given task type.

    Returns candidates sorted by score descending (best first).
    """
    if not candidates:
        return []

    task_key = resolve_task_key(task_type)
    complexity = compute_complexity(
        prompt,
        task_type,
        estimated_input_tokens=estimated_input_tokens,
    )
    weights = _score_weights(complexity)

    costs = [_blended_cost_per_1m(c.metadata) for c in candidates]
    latencies = [c.metadata["avg_latency_ms"] for c in candidates]

    scored: list[CandidateScore] = []
    for record, cost, latency in zip(candidates, costs, latencies):
        meta = record.metadata
        task_match = _compute_task_match(task_key, meta)
        cost_efficiency = _normalize_inverse(costs, cost)
        speed_score = _normalize_inverse(latencies, latency)
        reasoning_component = float(meta["reasoning_score"])
        preference_bonus = _task_preference_bonus(task_type, record.model_id)

        composite = (
            task_match * weights["task"]
            + cost_efficiency * weights["cost"]
            + speed_score * weights["speed"]
            + reasoning_component * weights["reasoning"]
            + preference_bonus
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
                task_preference_bonus=round(preference_bonus, 2),
                complexity_score=round(complexity, 2),
            )
        )

    scored.sort(key=lambda c: c.score, reverse=True)
    return scored


def pick_best_model(
    task_type: str,
    candidates: list[GroqModelRecord],
    *,
    prompt: str = "",
    estimated_input_tokens: int = 0,
) -> tuple[CandidateScore | None, list[CandidateScore]]:
    scored = score_candidates(
        task_type,
        candidates,
        prompt=prompt,
        estimated_input_tokens=estimated_input_tokens,
    )
    winner = scored[0] if scored else None
    return winner, scored
