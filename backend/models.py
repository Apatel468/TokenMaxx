"""
Pydantic models for API request/response validation.

These models define the shape of data going in and out of the API.
FastAPI uses them to validate requests and auto-generate OpenAPI docs.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    """POST /auth/signup body."""

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """POST /auth/login body."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Public user profile (never includes password)."""

    id: int
    email: str
    role: str
    created_at: str = ""
    enhance_prompts: bool = True


class UserPreferencesOut(BaseModel):
    """GET/PUT /user/preferences response."""

    enhance_prompts: bool = True


class UserPreferencesUpdate(BaseModel):
    """PUT /user/preferences body."""

    enhance_prompts: bool


class AuthResponse(BaseModel):
    """Returned after signup or login — includes JWT for the frontend."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut


class EmployeeUsageRecord(BaseModel):
    """One employee row for the admin dashboard."""

    user_id: int
    email: str
    total_chats: int
    total_input_tokens: int
    total_output_tokens: int
    actual_cost: float
    premium_baseline_cost: float
    savings: float
    savings_percentage: float
    most_used_models: list[str]


# ---------------------------------------------------------------------------
# Chat endpoint models
# ---------------------------------------------------------------------------

class RegenerateRequest(BaseModel):
    """POST /chat/regenerate — retry with a user-chosen model."""

    conversation_id: int
    message_id: int = Field(
        description="User message id for the turn being regenerated.",
    )
    model_id: str = Field(min_length=1)


class RegenerateResponse(BaseModel):
    """Response after regenerating with a user-selected model."""

    response: str
    model_used: str
    model_label: str = Field(
        default="",
        description="Human-readable model name for the UI.",
    )
    provider: str = "groq"
    task_type: str = ""
    regeneration_reason: str = Field(
        default="",
        description="Why this model was used (user-initiated regeneration).",
    )
    actual_cost: float
    premium_cost: float = 0.0
    savings_percentage: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float
    assistant_message_id: int
    response_label: str = "User Selected Model"
    was_user_selected: bool = True


class ModelRecommendation(BaseModel):
    """One ranked model in the top-5 recommendation list."""

    model_id: str
    provider: str
    ranking_score: float
    estimated_cost: float
    estimated_latency: float
    available: bool = True
    disabled_reason: str = ""


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
    enhance_prompt: bool = Field(
        default=True,
        description="When false, skip prompt enhancement and send the original prompt.",
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
    system_prompt: Optional[str] = Field(
        default="",
        description="System instructions applied for this task type (empty when enhancement disabled).",
    )
    enhancement_reason: str = Field(
        description="Short explanation of what enhancement rules were applied."
    )
    enhancement_method: str = Field(
        description='How the prompt was enhanced: "ai" or "rule_fallback".'
    )
    task_type: str
    classification_confidence: float = Field(
        default=0.0,
        description="Classifier confidence from 0.0 to 1.0.",
    )
    classification_reason: str = Field(
        default="",
        description="Short user-facing explanation of the task classification.",
    )
    classification_method: str = Field(
        default="rule_fallback",
        description='How the task was classified: "llm" or "rule_fallback".',
    )
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
        description="Full scored candidate list for debugging.",
    )
    top_candidate_scores: list[dict] = Field(
        default_factory=list,
        description="Top 3 routing scores for the Latest Routing debug panel.",
    )
    top_recommendations: list[ModelRecommendation] = Field(
        default_factory=list,
        description="Top 5 ranked models with cost/latency estimates and availability.",
    )
    selected_model_id: str = ""
    user_message_id: int = 0
    assistant_message_id: int = 0


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
    admin_enabled: bool = True
    user_enabled: bool = True
    disabled_by_admin: bool = False
    available: bool = True
    enabled: bool
    toggle_enabled: bool = True
    cost_per_1k_input: float
    cost_per_1k_output: float


class ModelControlToggle(BaseModel):
    """Single enable/disable change from Model Controls."""

    model_id: str
    enabled: bool = True


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
    enhancement_enabled_count: int = 0
    enhancement_disabled_count: int = 0
    enhancement_cost_saved: float = 0.0
    regeneration_count: int = 0


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
    enhancement_enabled: bool = True
    enhancement_method: str = ""
    timestamp: str = Field(
        description="Request time in America/New_York (e.g. 6/11/2026 9:28 AM EDT).",
    )


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
    timestamp: str = Field(
        description="Request time in America/New_York (e.g. 6/11/2026 9:28 AM EDT).",
    )


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
    response_label: str = ""
    selected_model: str = Field(
        default="",
        description="Model used for regenerated assistant replies (empty otherwise).",
    )
    original_prompt: str = Field(
        default="",
        description="User text before enhancement (assistant turns only).",
    )
    enhanced_prompt: str = Field(
        default="",
        description="Prompt sent to the model after optimization (assistant turns only).",
    )
    enhancement_method: str = Field(
        default="",
        description='How the prompt was enhanced: "ai", "rule_fallback", "disabled", or "reused".',
    )
    created_at: str = Field(
        description="Message time in America/New_York (e.g. 6/11/2026 9:28 AM EDT).",
    )


class ConversationListItem(BaseModel):
    """Summary row for GET /conversations."""

    id: int
    title: str = ""
    preview: str
    message_count: int
    created_at: str = Field(
        description="Created time in America/New_York (e.g. 6/11/2026 9:28 AM EDT).",
    )
    updated_at: str = Field(
        description="Last activity in America/New_York (e.g. 6/11/2026 9:28 AM EDT).",
    )


class ConversationDetail(BaseModel):
    """Full thread for GET /conversations/{id}."""

    id: int
    title: str = ""
    messages: list[MessageOut]
    created_at: str = Field(
        description="Created time in America/New_York (e.g. 6/11/2026 9:28 AM EDT).",
    )
    updated_at: str = Field(
        description="Last activity in America/New_York (e.g. 6/11/2026 9:28 AM EDT).",
    )
