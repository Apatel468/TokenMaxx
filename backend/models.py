"""
Pydantic models for API request/response validation.

These models define the shape of data going in and out of the API.
FastAPI uses them to validate requests and auto-generate OpenAPI docs.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat endpoint models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """What the client sends when calling POST /chat."""

    prompt: str = Field(
        ...,
        min_length=1,
        description="The user's message or question for the AI.",
        examples=["Summarize this article about climate change."],
    )
    # Optional — omit to start a new conversation; send to continue a thread
    conversation_id: Optional[int] = Field(
        default=None,
        description="Existing conversation id to append this message to.",
    )


class ChatResponse(BaseModel):
    """What the server returns after routing and generating a response."""

    conversation_id: int
    original_prompt: str
    task_type: str
    selected_model: str
    reason_selected: str
    mock_response: str
    estimated_actual_cost: float = Field(
        description="Estimated cost in USD for the model we chose."
    )
    estimated_premium_cost: float = Field(
        description="Estimated cost in USD if we had used the premium model."
    )
    estimated_savings_percentage: float = Field(
        description="How much cheaper the chosen model was vs. premium (0-100)."
    )


# ---------------------------------------------------------------------------
# Model catalog models
# ---------------------------------------------------------------------------

class ModelInfo(BaseModel):
    """Describes one AI model in our catalog."""

    id: str
    name: str
    provider: str
    tier: str  # "premium", "standard", or "economy"
    cost_per_1k_input: float
    cost_per_1k_output: float
    strengths: list[str]
    avg_latency_ms: int


# ---------------------------------------------------------------------------
# Analytics models (Phase 3)
# ---------------------------------------------------------------------------

class AnalyticsSummary(BaseModel):
    """High-level totals across all stored chat exchanges."""

    total_chats: int
    total_cost: float
    premium_baseline_cost: float
    total_savings: float
    savings_percentage: float


class HistoryRecord(BaseModel):
    """One chat request for GET /analytics/history."""

    id: int
    prompt: str
    response: str
    task_type: str
    selected_model: str
    actual_cost: float
    premium_cost: float
    savings_percentage: float
    timestamp: datetime

    class Config:
        from_attributes = True


class ConversationRecord(BaseModel):
    """One stored conversation with prompt, response, and metrics."""

    conversation_id: int
    prompt: str
    response: str
    task_type: str
    selected_model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    premium_model_cost: float
    savings: float
    savings_percentage: float
    latency_ms: float
    timestamp: datetime

    class Config:
        from_attributes = True


class ModelUsageRecord(BaseModel):
    """Usage stats grouped by Groq model."""

    model: str
    run_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    average_latency_ms: float


# ---------------------------------------------------------------------------
# Conversation memory models (Phase 3A)
# ---------------------------------------------------------------------------

class MessageOut(BaseModel):
    """One message in a conversation thread."""

    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Summary row for GET /conversations."""

    id: int
    preview: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """Full thread for GET /conversations/{id}."""

    id: int
    messages: list[MessageOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
