"""
Report Generator — builds analytics from conversations + model_runs tables.

Powers the GET /analytics/* endpoints.
"""

from sqlalchemy.orm import Session

from database import Conversation, Message, ModelRun
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


def get_conversations(db: Session, limit: int = 20) -> list[ConversationRecord]:
    """
    Return recent conversations with prompt, response, and routing info.

    Newest conversations appear first.
    """
    conversations = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )

    results: list[ConversationRecord] = []

    for conv in conversations:
        # Get user and assistant messages for this conversation
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        user_msg = next((m for m in messages if m.role == "user"), None)
        assistant_msg = next((m for m in messages if m.role == "assistant"), None)

        # Get routing + cost row
        run = (
            db.query(ModelRun)
            .filter(ModelRun.conversation_id == conv.id)
            .first()
        )

        if not run:
            continue

        results.append(
            ConversationRecord(
                conversation_id=conv.id,
                prompt=user_msg.content if user_msg else "",
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


def get_history(db: Session, limit: int = 20) -> list[HistoryRecord]:
    """
    Return recent chat history for GET /analytics/history.

    Same data as conversations, with field names matched to the API spec.
    """
    conversations = get_conversations(db, limit=limit)
    return [
        HistoryRecord(
            id=row.conversation_id,
            prompt=row.prompt,
            response=row.response,
            task_type=row.task_type,
            selected_model=row.selected_model,
            actual_cost=row.estimated_cost,
            premium_cost=row.premium_model_cost,
            savings_percentage=row.savings_percentage,
            timestamp=row.timestamp,
        )
        for row in conversations
    ]


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
