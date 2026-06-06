"""
Report Generator — builds analytics from conversations + model_runs tables.

Powers the GET /analytics/* endpoints.
"""

from sqlalchemy.orm import Session

from database import Message, ModelRun
from models import AnalyticsSummary, ConversationRecord, HistoryRecord, ModelUsageRecord


def generate_analytics_summary(db: Session) -> AnalyticsSummary:
    """
    Aggregate all model_runs into summary totals.

    Returns zeros when no chats exist yet.
    """
    runs = db.query(ModelRun).all()

    if not runs:
        return AnalyticsSummary(
            total_chats=0,
            total_cost=0.0,
            premium_baseline_cost=0.0,
            total_savings=0.0,
            savings_percentage=0.0,
        )

    total_cost = sum(r.estimated_cost for r in runs)
    premium_baseline_cost = sum(r.premium_model_cost for r in runs)
    total_savings = sum(r.savings_usd for r in runs)

    # Overall savings % vs. what premium would have cost
    if premium_baseline_cost > 0:
        savings_percentage = (total_savings / premium_baseline_cost) * 100
    else:
        savings_percentage = 0.0

    return AnalyticsSummary(
        total_chats=len(runs),
        total_cost=round(total_cost, 6),
        premium_baseline_cost=round(premium_baseline_cost, 6),
        total_savings=round(total_savings, 6),
        savings_percentage=round(savings_percentage, 2),
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


def get_model_run_records(db: Session, limit: int = 20) -> list[ConversationRecord]:
    """
    Return recent model runs — one row per AI reply (supports multi-turn).

    Includes enhanced_prompt from Phase 4 prompt engineering.
    """
    runs = (
        db.query(ModelRun)
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
                timestamp=run.created_at,
            )
        )

    return results


def get_conversations(db: Session, limit: int = 20) -> list[ConversationRecord]:
    """Return recent model runs (alias for analytics conversation rows)."""
    return get_model_run_records(db, limit=limit)


def get_history(db: Session, limit: int = 20) -> list[HistoryRecord]:
    """
    Return recent chat history for GET /analytics/history.

    Each row is one model_run (one turn), including enhanced_prompt when stored.
    """
    runs = (
        db.query(ModelRun)
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
                timestamp=run.created_at,
            )
        )

    return results


def get_model_usage(db: Session) -> list[ModelUsageRecord]:
    """
    Aggregate usage stats grouped by selected_model.

    Shows how often each Groq model was used and total cost per model.
    """
    runs = db.query(ModelRun).all()

    # Group runs by model name in Python (simple for MVP SQLite size)
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
