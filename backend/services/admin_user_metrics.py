"""
Admin user metrics — per-user usage aggregates for the admin dashboard.

Reuses model_runs, messages, conversations, and activity_logs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database import ActivityLog, Conversation, Message, ModelRun, User
from models import (
    AdminUserMetricsRecord,
    CategoryCount,
    FeatureUsageCount,
    ModelLatencyMetric,
    ModelUsageCount,
    PromptPeriodCount,
)
from services.activity_logger import _parse_date
from services.prompt_intelligence import normalize_task_type

SESSION_GAP_MINUTES = 30

QUERY_CATEGORIES = (
    "coding",
    "general_qa",
    "writing",
    "reasoning",
    "summarization",
    "research",
    "business",
    "education",
    "data_analysis",
)

FEATURE_EVENT_MAP: dict[str, tuple[str, ...]] = {
    "chat": ("chat_request_received",),
    "regenerate": ("regenerate_started",),
    "prompt_enhancement": ("prompt_enhancement_started",),
    "rag": ("rag_chunks_retrieved",),
    "document_upload": ("document_upload_started",),
    "model_controls": ("api_key_added", "api_key_tested", "api_key_deleted"),
}


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _period_key(dt: datetime, granularity: str) -> str:
    dt = _ensure_utc(dt)
    if granularity == "weekly":
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if granularity == "monthly":
        return dt.strftime("%Y-%m")
    return dt.strftime("%Y-%m-%d")


def compute_session_stats(timestamps: list[datetime]) -> tuple[int, float]:
    """Return (session_count, average_prompts_per_session) for sorted timestamps."""
    if not timestamps:
        return 0, 0.0

    ordered = sorted(_ensure_utc(ts) for ts in timestamps)
    gap = timedelta(minutes=SESSION_GAP_MINUTES)
    session_count = 1
    current_size = 1

    for index in range(1, len(ordered)):
        if ordered[index] - ordered[index - 1] > gap:
            session_count += 1
            current_size = 1
        else:
            current_size += 1

    avg = len(ordered) / session_count if session_count else 0.0
    return session_count, round(avg, 2)


def bucket_prompt_counts(
    timestamps: list[datetime],
    granularity: str,
) -> list[PromptPeriodCount]:
    counts: Counter[str] = Counter()
    for ts in timestamps:
        counts[_period_key(ts, granularity)] += 1
    return [
        PromptPeriodCount(period=period, count=count)
        for period, count in sorted(counts.items())
    ]


def _filter_by_date(query, column, start: datetime | None, end: datetime | None):
    if start:
        query = query.filter(column >= start)
    if end:
        query = query.filter(column <= end)
    return query


def _feature_usage_from_logs(logs: list[ActivityLog]) -> list[FeatureUsageCount]:
    event_to_feature = {
        event: feature
        for feature, events in FEATURE_EVENT_MAP.items()
        for event in events
    }
    counts: Counter[str] = Counter()
    for row in logs:
        feature = event_to_feature.get(row.event_type)
        if feature:
            counts[feature] += 1
    return [
        FeatureUsageCount(feature=feature, count=counts.get(feature, 0))
        for feature in FEATURE_EVENT_MAP
    ]


def _feature_usage_from_runs(runs: list[ModelRun]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for run in runs:
        if run.is_regeneration:
            counts["regenerate"] += 1
        else:
            counts["chat"] += 1
        if run.enhancement_enabled:
            counts["prompt_enhancement"] += 1
        if run.rag_used:
            counts["rag"] += 1
    return counts


def _merge_feature_usage(
    log_features: list[FeatureUsageCount],
    run_counts: Counter[str],
) -> list[FeatureUsageCount]:
    merged: dict[str, int] = {item.feature: item.count for item in log_features}
    for feature, count in run_counts.items():
        merged[feature] = max(merged.get(feature, 0), count)
    return [
        FeatureUsageCount(feature=feature, count=merged.get(feature, 0))
        for feature in FEATURE_EVENT_MAP
    ]


def _category_counts(runs: list[ModelRun]) -> list[CategoryCount]:
    counts: Counter[str] = Counter()
    for run in runs:
        category = normalize_task_type(run.task_type)
        if category not in QUERY_CATEGORIES:
            category = "general_qa"
        counts[category] += 1
    return [
        CategoryCount(category=category, count=counts.get(category, 0))
        for category in QUERY_CATEGORIES
        if counts.get(category, 0) > 0
    ]


def _model_usage(runs: list[ModelRun]) -> list[ModelUsageCount]:
    counts = Counter(run.selected_model for run in runs)
    return [
        ModelUsageCount(model=model, run_count=count)
        for model, count in counts.most_common()
    ]


def _latency_by_model(runs: list[ModelRun]) -> list[ModelLatencyMetric]:
    totals: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        totals[run.selected_model].append(float(run.latency_ms))
    results: list[ModelLatencyMetric] = []
    for model, values in sorted(totals.items()):
        avg = sum(values) / len(values) if values else 0.0
        results.append(
            ModelLatencyMetric(
                model=model,
                run_count=len(values),
                average_latency_ms=round(avg, 1),
            )
        )
    results.sort(key=lambda item: item.run_count, reverse=True)
    return results


def _metrics_for_user(
    db: Session,
    user: User,
    *,
    start: datetime | None,
    end: datetime | None,
    granularity: str,
) -> AdminUserMetricsRecord:
    message_query = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user.id, Message.role == "user")
    )
    message_query = _filter_by_date(message_query, Message.created_at, start, end)
    user_messages = message_query.order_by(Message.created_at.asc()).all()
    prompt_times = [m.created_at for m in user_messages if m.created_at]

    run_query = db.query(ModelRun).filter(ModelRun.user_id == user.id)
    run_query = _filter_by_date(run_query, ModelRun.created_at, start, end)
    runs = run_query.all()

    log_query = db.query(ActivityLog).filter(ActivityLog.user_id == user.id)
    log_query = _filter_by_date(log_query, ActivityLog.created_at, start, end)
    logs = log_query.all()

    session_count, avg_per_session = compute_session_stats(prompt_times)
    model_usage = _model_usage(runs)
    latency_by_model = _latency_by_model(runs)
    categories = _category_counts(runs)
    feature_usage = _merge_feature_usage(
        _feature_usage_from_logs(logs),
        _feature_usage_from_runs(runs),
    )

    total_input = sum(r.input_tokens for r in runs)
    total_output = sum(r.output_tokens for r in runs)
    total_tokens = total_input + total_output
    actual_cost = sum(r.estimated_cost for r in runs)
    premium_cost = sum(r.premium_model_cost for r in runs)
    savings = sum(r.savings_usd for r in runs)
    savings_pct = (savings / premium_cost * 100) if premium_cost > 0 else 0.0

    overall_latency = (
        sum(r.latency_ms for r in runs) / len(runs) if runs else 0.0
    )

    return AdminUserMetricsRecord(
        user_id=user.id,
        email=user.email,
        role=user.role,
        total_prompts=len(user_messages),
        prompts_over_time=bucket_prompt_counts(prompt_times, granularity),
        session_count=session_count,
        average_prompts_per_session=avg_per_session,
        most_used_models=model_usage,
        average_latency_by_model=latency_by_model,
        feature_usage=feature_usage,
        query_categories=categories,
        total_tokens=total_tokens,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_actual_cost=round(actual_cost, 6),
        total_premium_cost=round(premium_cost, 6),
        total_savings=round(savings, 6),
        savings_percentage=round(savings_pct, 2),
        top_model=model_usage[0].model if model_usage else "",
        top_category=(
            max(categories, key=lambda item: item.count).category if categories else ""
        ),
        average_latency_ms=round(overall_latency, 1),
    )


def get_admin_user_metrics(
    db: Session,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    user_id: int | None = None,
    granularity: str = "daily",
) -> list[AdminUserMetricsRecord]:
    """Build per-user admin metrics with optional filters."""
    granularity = granularity if granularity in {"daily", "weekly", "monthly"} else "daily"
    start = _parse_date(start_date)
    end = _parse_date(end_date, end_of_day=True)

    query = db.query(User).order_by(User.email.asc())
    if user_id is not None:
        query = query.filter(User.id == user_id)
    users = query.all()

    return [
        _metrics_for_user(db, user, start=start, end=end, granularity=granularity)
        for user in users
    ]
