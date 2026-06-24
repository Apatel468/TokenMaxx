"""
Model Scorer — ranks models for a task type with complexity-aware weights.

Composite score blends task fit, quality, speed, cost, and task-specific bonuses.
Cheap/fast models are favored for simple general Q&A; business/report/coding
tasks can prefer premium models when complexity and bonuses warrant it.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.model_registry import ModelMetadata
from services.config_loader import get_scoring_weights, get_task_profile, resolve_task_key
from services.groq_models import GroqModelRecord

# Task-specific preference bonuses (added to composite — steers routing per task).
TASK_MODEL_BONUSES: dict[str, dict[str, float]] = {
    "general_qa": {
        "llama-3.1-8b-instant": 14.0,
        "openai/gpt-oss-20b": 8.0,
        "gpt-4o": -8.0,
        "claude-3-5-sonnet": -10.0,
        "o3-mini": -6.0,
    },
    "classification": {
        "llama-3.1-8b-instant": 14.0,
    },
    "coding": {
        "qwen/qwen3-32b": 14.0,
        "gpt-4o": 12.0,
        "claude-3-5-sonnet": 12.0,
        "o3-mini": 10.0,
    },
    "math": {
        "qwen/qwen3-32b": 16.0,
    },
    "reasoning": {
        "openai/gpt-oss-120b": 14.0,
        "o3-mini": 10.0,
        "gpt-4o": 6.0,
        "claude-3-5-sonnet": 8.0,
        "qwen/qwen3-32b": 5.0,
    },
    "writing": {
        "llama-3.3-70b-versatile": 12.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 10.0,
        "claude-3-5-sonnet": 8.0,
        "gpt-4o": 5.0,
    },
    "summarization": {
        "llama-3.1-8b-instant": 10.0,
        "llama-3.3-70b-versatile": 9.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 8.0,
    },
    "business": {
        "claude-3-5-sonnet": 16.0,
        "gpt-4o": 14.0,
        "o3-mini": 10.0,
        "llama-3.3-70b-versatile": 8.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 7.0,
        "qwen/qwen3-32b": 4.0,
        "llama-3.1-8b-instant": -8.0,
        "openai/gpt-oss-20b": -5.0,
    },
    "report": {
        "claude-3-5-sonnet": 15.0,
        "gpt-4o": 13.0,
        "llama-3.3-70b-versatile": 10.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 9.0,
        "openai/gpt-oss-20b": -4.0,
        "llama-3.1-8b-instant": -8.0,
    },
    "creative": {
        "llama-3.3-70b-versatile": 11.0,
        "meta-llama/llama-4-scout-17b-16e-instruct": 9.0,
    },
    "research": {
        "openai/gpt-oss-120b": 12.0,
        "llama-3.3-70b-versatile": 7.0,
    },
    "web_research": {
        "openai/gpt-oss-120b": 18.0,
        "llama-3.3-70b-versatile": 15.0,
        "qwen/qwen3-32b": 12.0,
        "llama-3.1-8b-instant": -6.0,
    },
}

_COMPLEX_TASK_TYPES = frozenset(
    {
        "reasoning",
        "research",
        "math",
        "coding",
        "report",
        "creative",
        "writing",
        "business",
        "web_research",
    }
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
    "detailed",
    "comprehensive",
    "enterprise",
    "fortune 500",
    "strategy",
    "compare",
    "evaluate",
    "roadmap",
    "risks",
    "stakeholders",
    "financial impact",
)

_STRATEGY_REPORT_KEYWORDS = (
    "business strategy",
    "fortune 500",
    "executive strategy",
    "market strategy",
    "go-to-market",
    "go to market",
    "competitive analysis",
    "rfp",
    "proposal",
    "enterprise",
    "board presentation",
    "risk analysis",
    "implementation roadmap",
    "compliance",
    "procurement",
    "strategic plan",
    "executive report",
    "stakeholder",
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
    writing_score: float = 0.0
    provider: str = "groq"
    task_preference_bonus: float = 0.0
    complexity_score: float = 0.0
    provider_key_available: bool = True

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "score": round(self.score, 2),
            "task_match": round(self.task_match, 2),
            "cost_efficiency": round(self.cost_efficiency, 2),
            "speed_score": round(self.speed_score, 2),
            "reasoning_score": round(self.reasoning_score, 2),
            "writing_score": round(self.writing_score, 2),
            "task_preference_bonus": round(self.task_preference_bonus, 2),
            "complexity_score": round(self.complexity_score, 2),
            "provider": self.provider,
            "provider_key_available": self.provider_key_available,
        }


def complexity_level(complexity: float) -> str:
    """Map complexity score to a human-readable band."""
    if complexity >= 0.65:
        return "high"
    if complexity >= 0.35:
        return "medium"
    return "low"


def infer_task_type_from_prompt(prompt: str, task_type: str) -> str:
    """Boost misclassified prompts toward business/report when strategy keywords hit."""
    if task_type in {"business", "report"}:
        return task_type
    text = (prompt or "").strip().lower()
    strategy_hits = sum(1 for kw in _STRATEGY_REPORT_KEYWORDS if kw in text)
    if strategy_hits >= 2:
        return "business"
    if strategy_hits == 1 and any(
        word in text for word in ("detailed", "comprehensive", "strategy", "enterprise")
    ):
        return "business"
    return task_type


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
    task_factor = 0.32 if task_type in _COMPLEX_TASK_TYPES else 0.0
    structure_bonus = 0.12 if len(text) > 400 else 0.0

    if any(keyword in text for keyword in _COMPLEXITY_KEYWORDS):
        structure_bonus += 0.14

    strategy_hits = sum(1 for kw in _STRATEGY_REPORT_KEYWORDS if kw in text)
    if strategy_hits:
        structure_bonus += min(0.10 + strategy_hits * 0.06, 0.28)

    if task_type in {"business", "report"}:
        task_factor = max(task_factor, 0.36)

    return min(length_factor * 0.5 + task_factor + structure_bonus, 1.0)


def _task_preference_bonus(task_type: str, model_id: str) -> float:
    resolved = resolve_task_key(task_type)
    for key in (task_type, resolved):
        bonuses = TASK_MODEL_BONUSES.get(key)
        if bonuses and model_id in bonuses:
            return bonuses[model_id]
    return 0.0


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


def filter_candidates_by_provider_keys(
    candidates: list[GroqModelRecord],
    *,
    db=None,
    user_id: int | None = None,
) -> tuple[list[GroqModelRecord], dict[str, bool]]:
    """
    Keep only models whose provider has a user or app-level API key.

    Returns (filtered_candidates, provider_availability_map).
    If no provider has keys, returns all candidates (mock/demo fallback).
    """
    from services.model_clients import has_provider_key

    availability: dict[str, bool] = {}
    for record in candidates:
        provider = record.metadata["provider"]
        if provider not in availability:
            availability[provider] = has_provider_key(db, user_id, provider)

    keyed = [r for r in candidates if availability.get(r.metadata["provider"], False)]
    if keyed:
        return keyed, availability
    return candidates, availability


def score_candidates(
    task_type: str,
    candidates: list[GroqModelRecord],
    *,
    prompt: str = "",
    estimated_input_tokens: int = 0,
    db=None,
    user_id: int | None = None,
) -> list[CandidateScore]:
    """
    Score every candidate model for the given task type.

    Returns candidates sorted by score descending (best first).
    """
    if not candidates:
        return []

    effective_task = infer_task_type_from_prompt(prompt, task_type)
    task_key = resolve_task_key(effective_task)
    complexity = compute_complexity(
        prompt,
        effective_task,
        estimated_input_tokens=estimated_input_tokens,
    )
    weights = get_scoring_weights(effective_task, complexity)

    score_pool, provider_availability = filter_candidates_by_provider_keys(
        candidates, db=db, user_id=user_id
    )

    costs = [_blended_cost_per_1m(c.metadata) for c in score_pool]
    latencies = [c.metadata["avg_latency_ms"] for c in score_pool]

    scored: list[CandidateScore] = []
    for record, cost, latency in zip(score_pool, costs, latencies):
        meta = record.metadata
        provider = meta["provider"]
        task_match = _compute_task_match(task_key, meta)
        cost_efficiency = _normalize_inverse(costs, cost)
        speed_score = _normalize_inverse(latencies, latency)
        reasoning_component = float(meta["reasoning_score"])
        writing_component = float(meta["writing_score"])
        preference_bonus = _task_preference_bonus(effective_task, record.model_id)
        key_available = provider_availability.get(provider, False)

        composite = (
            task_match * weights["task"]
            + reasoning_component * weights["reasoning"]
            + writing_component * weights.get("writing", 0.0)
            + cost_efficiency * weights["cost"]
            + speed_score * weights["speed"]
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
                writing_score=writing_component,
                provider=provider,
                task_preference_bonus=round(preference_bonus, 2),
                complexity_score=round(complexity, 2),
                provider_key_available=key_available,
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
    db=None,
    user_id: int | None = None,
) -> tuple[CandidateScore | None, list[CandidateScore]]:
    scored = score_candidates(
        task_type,
        candidates,
        prompt=prompt,
        estimated_input_tokens=estimated_input_tokens,
        db=db,
        user_id=user_id,
    )
    winner = scored[0] if scored else None
    return winner, scored


def build_routing_explanation(
    *,
    task_type: str,
    task_key: str,
    complexity: float,
    winner: CandidateScore,
    preferred: CandidateScore | None,
    provider_availability: dict[str, bool],
) -> list[str]:
    """Human-readable bullets for the routing panel."""
    lines = [
        f"Task classified as {task_type} (profile: {task_key}).",
        f"Complexity {complexity_level(complexity)} ({complexity:.2f}).",
    ]
    available = [p for p, ok in sorted(provider_availability.items()) if ok]
    unavailable = [p for p, ok in sorted(provider_availability.items()) if not ok]
    if available:
        lines.append(f"Provider keys available: {', '.join(available)}.")
    if unavailable:
        lines.append(
            f"No API key for: {', '.join(unavailable)} — those models were excluded."
        )
    if preferred and preferred.model_id != winner.model_id:
        lines.append(
            f"Highest raw score was {preferred.model_id} ({preferred.score:.1f}) "
            f"but {winner.model_id} was selected among enabled, keyed models."
        )
    elif winner.task_preference_bonus > 0:
        lines.append(
            f"Premium/task bonus (+{winner.task_preference_bonus:.0f}) "
            f"favored {winner.model_id}."
        )
    elif winner.task_preference_bonus < 0:
        lines.append(
            f"Economy bonus favored {winner.model_id} over premium models."
        )
    else:
        lines.append(f"Balanced score favored {winner.model_id}.")
    return lines
