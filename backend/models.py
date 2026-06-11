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
    title: str = Field(
        default="",
        description="Conversation title (set after the first assistant reply).",
    )
    original_prompt: str
    enhanced_prompt: str = Field(
        description="Task-wrapped prompt sent to the LLM (user intent preserved)."
    )
    system_prompt: str = Field(
        description="System instructions applied for this task type."
    )
    enhancement_reason: str = Field(
        description="Short explanation of what enhancement rules were applied."
    )
    enhancement_method: str = Field(
        description='How the prompt was enhanced: "ai" or "rule_fallback".'
    )
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
    preferred_model: str = Field(
        default="",
        description="Model that would have been chosen before enable/disable rules.",
    )
    used_fallback: bool = Field(
        default=False,
        description="True when a different enabled model was used because preferred was disabled.",
    )
    fallback_message: str = Field(
        default="",
        description='Set to "Preferred model disabled — fallback used" when applicable.',
    )
    routing_score: float = Field(
        default=0.0,
        description="Composite routing score (0–100) for the selected model.",
    )
    candidate_models: list[dict] = Field(
        default_factory=list,
        description="All scored candidates: model_id, score, task_match, etc.",
    )


# ---------------------------------------------------------------------------
# Model catalog models
# ---------------------------------------------------------------------------

class ModelControlItem(BaseModel):
    """One routable model row in Model Controls."""

    model_id: str
    name: str
    provider: str
    tier: str
    task_types: list[str]
    enabled: bool
    cost_per_1k_input: float
    cost_per_1k_output: float


class ModelControlToggle(BaseModel):
    """Single enable/disable change from Model Controls."""

    model_id: str
    enabled: bool


class ModelControlsUpdate(BaseModel):
    """Bulk update for model enable/disable toggles."""

    models: list[ModelControlToggle]


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


class ModelSyncSummary(BaseModel):
    """Result of GET /models/sync — Groq API vs registry comparison."""

    total: int
    routable: int
    in_registry: int
    in_groq_api: int
    missing_from_registry: list[str]


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
    enhanced_prompt: str = ""
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
    enhanced_prompt: str = ""
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
    title: str = ""
    preview: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """Full thread for GET /conversations/{id}."""

    id: int
    title: str = ""
    messages: list[MessageOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
