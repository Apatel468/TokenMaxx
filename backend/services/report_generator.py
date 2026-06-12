"""
Report Generator — builds analytics from conversations + model_runs tables.

Regular users only see their own runs; admins use get_employee_usage_metrics()
for organization-wide employee usage on the admin dashboard.
"""

from collections import Counter

from sqlalchemy.orm import Session

from database import Message, ModelRun, User
from models import (
    AnalyticsSummary,
    ConversationRecord,
    EmployeeUsageRecord,
    HistoryRecord,
    ModelUsageRecord,
)
from services.timezone_utils import format_timestamp_eastern


def _runs_for_user(db: Session, user_id: int):
    """Base query: model_runs belonging to one user."""
    return db.query(ModelRun).filter(ModelRun.user_id == user_id)


def generate_analytics_summary(db: Session, user_id: int) -> AnalyticsSummary:
    """
    Aggregate one user's model_runs into summary totals.

    Returns zeros when no chats exist yet.
    """
    runs = _runs_for_user(db, user_id).all()

    if not runs:
        return AnalyticsSummary(
            total_chats=0,
            total_cost=0.0,
            premium_baseline_cost=0.0,
            total_savings=0.0,
            savings_percentage=0.0,
            enhancement_enabled_count=0,
            enhancement_disabled_count=0,
            enhancement_cost_saved=0.0,
            regeneration_count=0,
        )

    total_cost = sum(r.estimated_cost for r in runs)
    premium_baseline_cost = sum(r.premium_model_cost for r in runs)
    total_savings = sum(r.savings_usd for r in runs)

    if premium_baseline_cost > 0:
        savings_percentage = (total_savings / premium_baseline_cost) * 100
    else:
        savings_percentage = 0.0

    enabled_count = sum(1 for r in runs if getattr(r, "enhancement_enabled", True))
    disabled_count = len(runs) - enabled_count
    enhancement_cost_saved = sum(
        getattr(r, "enhancement_cost_saved", 0.0) or 0.0 for r in runs
    )
    regeneration_count = sum(1 for r in runs if getattr(r, "is_regeneration", False))

    return AnalyticsSummary(
        total_chats=len(runs),
        total_cost=round(total_cost, 6),
        premium_baseline_cost=round(premium_baseline_cost, 6),
        total_savings=round(total_savings, 6),
        savings_percentage=round(savings_percentage, 2),
        enhancement_enabled_count=enabled_count,
        enhancement_disabled_count=disabled_count,
        enhancement_cost_saved=round(enhancement_cost_saved, 6),
        regeneration_count=regeneration_count,
    )


def _get_user_message_for_run(db: Session, run: ModelRun) -> Message | None:
    """Find the user message that belongs to the same turn as this model_run."""
    if not run.assistant_message_id:
        return None

    assistant_msg = db.query(Message).filter(Message.id == run.assistant_message_id).first()
    if not assistant_msg:
        return None

    return (
        db.query(Message)
        .filter(
            Message.conversation_id == run.conversation_id,
            Message.role == "user",
            Message.created_at <= assistant_msg.created_at,
        )
        .order_by(Message.created_at.desc())
        .first()
    )


def get_model_run_records(
    db: Session, user_id: int, limit: int = 20
) -> list[ConversationRecord]:
    """Return recent model runs for one user — one row per AI reply."""
    runs = (
        _runs_for_user(db, user_id)
        .order_by(ModelRun.created_at.desc())
        .limit(limit)
        .all()
    )

    results: list[ConversationRecord] = []
    for run in runs:
        user_msg = _get_user_message_for_run(db, run)
        assistant_msg = (
            db.query(Message).filter(Message.id == run.assistant_message_id).first()
        )

        results.append(
            ConversationRecord(
                conversation_id=run.conversation_id,
                prompt=user_msg.content if user_msg else "",
                enhanced_prompt=run.enhanced_prompt or "",
                response=assistant_msg.content if assistant_msg else "",
                task_type=run.task_type,
                selected_model=run.selected_model,
                input_tokens=run.input_tokens,
                output_tokens=run.output_tokens,
                estimated_cost=run.estimated_cost,
                premium_model_cost=run.premium_model_cost,
                savings=run.savings_usd,
                savings_percentage=run.savings_percentage,
                latency_ms=run.latency_ms,
                timestamp=format_timestamp_eastern(run.created_at),
            )
        )

    return results


def get_conversations(
    db: Session, user_id: int, limit: int = 20
) -> list[ConversationRecord]:
    """Return recent model runs (alias for analytics conversation rows)."""
    return get_model_run_records(db, user_id, limit=limit)


def get_history(db: Session, user_id: int, limit: int = 20) -> list[HistoryRecord]:
    """Return recent chat history for GET /analytics/history (scoped to one user)."""
    runs = (
        _runs_for_user(db, user_id)
        .order_by(ModelRun.created_at.desc())
        .limit(limit)
        .all()
    )

    results: list[HistoryRecord] = []
    for run in runs:
        user_msg = _get_user_message_for_run(db, run)
        assistant_msg = (
            db.query(Message).filter(Message.id == run.assistant_message_id).first()
        )
        results.append(
            HistoryRecord(
                id=run.id,
                prompt=user_msg.content if user_msg else "",
                enhanced_prompt=run.enhanced_prompt or "",
                response=assistant_msg.content if assistant_msg else "",
                task_type=run.task_type,
                selected_model=run.selected_model,
                actual_cost=run.estimated_cost,
                premium_cost=run.premium_model_cost,
                savings_percentage=run.savings_percentage,
                enhancement_enabled=bool(getattr(run, "enhancement_enabled", True)),
                enhancement_method=run.enhancement_method or "",
                timestamp=format_timestamp_eastern(run.created_at),
            )
        )

    return results


def get_model_usage(db: Session, user_id: int) -> list[ModelUsageRecord]:
    """Aggregate usage stats grouped by selected_model for one user."""
    runs = _runs_for_user(db, user_id).all()

    stats: dict[str, dict] = {}
    for run in runs:
        if run.selected_model not in stats:
            stats[run.selected_model] = {
                "run_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost": 0.0,
                "latency_sum": 0.0,
            }
        bucket = stats[run.selected_model]
        bucket["run_count"] += 1
        bucket["input_tokens"] += run.input_tokens
        bucket["output_tokens"] += run.output_tokens
        bucket["total_cost"] += run.estimated_cost
        bucket["latency_sum"] += run.latency_ms

    results = []
    for model, data in sorted(stats.items()):
        avg_latency = (
            data["latency_sum"] / data["run_count"] if data["run_count"] else 0
        )
        results.append(
            ModelUsageRecord(
                model=model,
                run_count=data["run_count"],
                total_input_tokens=data["input_tokens"],
                total_output_tokens=data["output_tokens"],
                total_cost=round(data["total_cost"], 6),
                average_latency_ms=round(avg_latency, 1),
            )
        )

    return results


def get_employee_usage_metrics(db: Session) -> list[EmployeeUsageRecord]:
    """
    Admin dashboard: per-user totals across all model_runs.

    Includes most-used models (top 3) for each employee.
    """
    users = db.query(User).order_by(User.email.asc()).all()
    records: list[EmployeeUsageRecord] = []

    for user in users:
        runs = _runs_for_user(db, user.id).all()
        total_input = sum(r.input_tokens for r in runs)
        total_output = sum(r.output_tokens for r in runs)
        actual_cost = sum(r.estimated_cost for r in runs)
        premium_cost = sum(r.premium_model_cost for r in runs)
        savings = sum(r.savings_usd for r in runs)
        savings_pct = (savings / premium_cost * 100) if premium_cost > 0 else 0.0

        model_counts = Counter(r.selected_model for r in runs)
        most_used = [name for name, _ in model_counts.most_common(3)]

        records.append(
            EmployeeUsageRecord(
                user_id=user.id,
                email=user.email,
                total_chats=len(runs),
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                actual_cost=round(actual_cost, 6),
                premium_baseline_cost=round(premium_cost, 6),
                savings=round(savings, 6),
                savings_percentage=round(savings_pct, 2),
                most_used_models=most_used,
            )
        )

    return records
