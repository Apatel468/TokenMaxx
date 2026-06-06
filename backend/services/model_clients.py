"""
Model Clients — send prompts to Groq via LiteLLM (Phase 2).

Flow for every request:
  1. Router picks a Groq model from config/models.yaml.
  2. Check if GROQ_API_KEY is set in the environment (.env loaded at startup).
  3. If yes  → litellm.completion() with groq/<model> → real response.
  4. If no   → mock response (app still works for demos).

We never read .env directly — python-dotenv loads keys into os.environ
and we only check whether GROQ_API_KEY is present (not its value).
"""

import logging
import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv

from services.context_builder import PromptContext

# Load .env into environment variables once at import time
load_dotenv()

logger = logging.getLogger(__name__)

# Only Groq is used in Phase 2
GROQ_ENV_KEY = "GROQ_API_KEY"


@dataclass
class ModelResponse:
    """Unified response — works for both real Groq and mock completions."""

    text: str
    estimated_output_tokens: int
    input_tokens: int | None = None
    is_mock: bool = False
    latency_ms: float = 0.0
    litellm_model: str = ""


# Mock templates when GROQ_API_KEY is missing or the API call fails
_MOCK_TEMPLATES: dict[str, str] = {
    "coding": "Starter code approach for your request...",
    "flashcards": "Card 1\nQ: Key term?\nA: Definition.",
    "general_qa": "Here is a concise answer to your question.",
    "report": "Report draft with introduction, findings, and conclusion.",
    "summarization": "Summary with key bullet points.",
    "creative_writing": "Creative draft based on your prompt.",
    "data_analysis": "Analysis outline with trends and recommendations.",
    "translation": "[Translated text would appear here]",
}


def _has_groq_key() -> bool:
    """
    Return True if GROQ_API_KEY exists in the environment.

    We only check presence — never log or expose the key value.
    """
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def _to_litellm_model(groq_model: str) -> str:
    """
    Convert YAML model name to LiteLLM format.

    Examples:
      llama-3.3-70b-versatile  → groq/llama-3.3-70b-versatile
      qwen/qwen3-32b           → groq/qwen/qwen3-32b
    """
    if groq_model.startswith("groq/"):
        return groq_model
    return f"groq/{groq_model}"


def _call_groq(
    groq_model: str,
    context: PromptContext,
    messages: list[dict] | None = None,
) -> ModelResponse:
    """
    Call Groq through LiteLLM.

    Uses full conversation history when provided (Phase 3A multi-turn).
    """
    import litellm

    litellm_model = _to_litellm_model(groq_model)
    # Full thread for follow-ups, or single user message for new chats
    litellm_messages = messages or context.message_history or [
        {"role": "user", "content": context.prompt}
    ]

    start = time.perf_counter()
    response = litellm.completion(model=litellm_model, messages=litellm_messages)
    latency_ms = (time.perf_counter() - start) * 1000

    text = response.choices[0].message.content or ""
    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else None
    output_tokens = (
        usage.completion_tokens if usage else max(len(text) // 4, 1)
    )

    return ModelResponse(
        text=text,
        estimated_output_tokens=output_tokens,
        input_tokens=input_tokens,
        is_mock=False,
        latency_ms=round(latency_ms, 1),
        litellm_model=litellm_model,
    )


def _generate_mock_response(groq_model: str, context: PromptContext) -> ModelResponse:
    """Canned response when GROQ_API_KEY is missing or Groq returns an error."""
    start = time.perf_counter()

    base = _MOCK_TEMPLATES.get(context.task_type, _MOCK_TEMPLATES["general_qa"])
    text = (
        f"[Mock response — Groq / {groq_model}]\n\n"
        f"Task: {context.task_type}\n\n"
        f"{base}\n\n"
        f"---\n"
        f"Set GROQ_API_KEY in backend/.env for real Groq responses."
    )
    output_tokens = max(len(text) // 4, 1)
    latency_ms = (time.perf_counter() - start) * 1000

    return ModelResponse(
        text=text,
        estimated_output_tokens=output_tokens,
        input_tokens=None,
        is_mock=True,
        latency_ms=round(latency_ms, 1),
        litellm_model="mock",
    )


def generate_response(
    groq_model: str,
    context: PromptContext,
    messages: list[dict] | None = None,
) -> ModelResponse:
    """
    Main entry point — called by POST /chat after the router picks a model.

    Pass `messages` for multi-turn chats (full history including new user msg).
    """
    if not _has_groq_key():
        logger.info(
            "Mock fallback | groq_model=%s | reason=%s not set",
            groq_model,
            GROQ_ENV_KEY,
        )
        return _generate_mock_response(groq_model, context)

    try:
        result = _call_groq(groq_model, context, messages=messages)
        logger.info(
            "Groq success | model=%s | input_tokens=%s | output_tokens=%s | "
            "latency_ms=%.1f",
            result.litellm_model,
            result.input_tokens,
            result.estimated_output_tokens,
            result.latency_ms,
        )
        return result
    except Exception as exc:
        logger.warning(
            "Groq call failed | model=%s | error=%s — using mock",
            groq_model,
            exc,
        )
        return _generate_mock_response(groq_model, context)
