"""
Model Clients — send prompts to LLM providers via LiteLLM.

Flow for every request:
  1. Router picks a model from model_registry.py (any enabled provider).
  2. Resolve API key: user key first, then app-level env key for that provider.
  3. If yes  → litellm.completion() with provider-specific model id.
  4. If no   → mock response (when ALLOW_MOCK_LLM=true).
"""

import logging
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass

from dotenv import load_dotenv

from config.model_registry import get_provider_for_model, to_litellm_model
from services.context_builder import PromptContext
from services.response_cleaner import clean_model_response

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_ENV_KEY = "GROQ_API_KEY"


class MissingApiKeyError(Exception):
    """Raised when no user or app-level API key exists for a provider."""

    def __init__(self, provider: str, detail: str | None = None):
        self.provider = provider
        self.detail = detail or (
            f"No API key configured for provider '{provider}'. "
            "Add a key under API Keys or set the app-level environment variable."
        )
        super().__init__(self.detail)


_QWEN_MODEL_ID = "qwen/qwen3-32b"
_QWEN_SYSTEM_SUFFIX = (
    "Do not include internal reasoning, chain-of-thought, or <think> tags. "
    "Only provide the final answer."
)


@dataclass
class ModelResponse:
    """Unified response — works for real API and mock completions."""

    text: str
    estimated_output_tokens: int
    input_tokens: int | None = None
    is_mock: bool = False
    latency_ms: float = 0.0
    litellm_model: str = ""
    provider: str = "groq"


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


def _allow_mock_fallback() -> bool:
    return os.getenv("ALLOW_MOCK_LLM", "true").lower() in ("1", "true", "yes")


def _provider_for_model(model_id: str) -> str:
    return get_provider_for_model(model_id)


def _resolve_api_key(db, user_id: int | None, provider: str) -> str | None:
    from services.api_key_service import resolve_api_key

    return resolve_api_key(db, user_id, provider)


def _has_groq_key() -> bool:
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def _has_provider_key(db, user_id: int | None, provider: str) -> bool:
    return bool(_resolve_api_key(db, user_id, provider))


def has_provider_key(db, user_id: int | None, provider: str) -> bool:
    """Public check for whether a provider key is configured."""
    return _has_provider_key(db, user_id, provider)


def _is_qwen_model(model_id: str) -> bool:
    normalized = model_id.lower().replace("groq/", "")
    return "qwen" in normalized or normalized == _QWEN_MODEL_ID


def _build_system_prompt(context: PromptContext, model_id: str) -> str:
    parts: list[str] = []
    if context.system_prompt:
        parts.append(context.system_prompt.strip())
    if _is_qwen_model(model_id):
        parts.append(_QWEN_SYSTEM_SUFFIX)
    return "\n\n".join(parts)


def _build_litellm_messages(
    context: PromptContext,
    model_id: str,
    messages: list[dict] | None = None,
) -> list[dict]:
    history = messages or context.message_history or [
        {"role": "user", "content": context.enhanced_prompt or context.prompt}
    ]

    litellm_messages: list[dict] = []
    system_prompt = _build_system_prompt(context, model_id)
    if system_prompt:
        litellm_messages.append({"role": "system", "content": system_prompt})
    litellm_messages.extend(history)
    return litellm_messages


def _finalize_response(response: ModelResponse) -> ModelResponse:
    cleaned = clean_model_response(response.text)
    if cleaned != response.text:
        logger.info(
            "Response cleanup | removed thinking tags | %d -> %d chars",
            len(response.text),
            len(cleaned),
        )
    return ModelResponse(
        text=cleaned,
        estimated_output_tokens=response.estimated_output_tokens,
        input_tokens=response.input_tokens,
        is_mock=response.is_mock,
        latency_ms=response.latency_ms,
        litellm_model=response.litellm_model,
        provider=response.provider,
    )


def _call_provider(
    model_id: str,
    context: PromptContext,
    messages: list[dict] | None = None,
    *,
    api_key: str | None = None,
    provider: str | None = None,
) -> ModelResponse:
    import litellm

    resolved_provider = provider or _provider_for_model(model_id)
    litellm_model = to_litellm_model(model_id)
    litellm_messages = _build_litellm_messages(context, model_id, messages=messages)

    start = time.perf_counter()
    kwargs: dict = {"model": litellm_model, "messages": litellm_messages}
    if api_key:
        kwargs["api_key"] = api_key
    response = litellm.completion(**kwargs)
    latency_ms = (time.perf_counter() - start) * 1000

    raw_text = response.choices[0].message.content or ""
    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else None
    output_tokens = (
        usage.completion_tokens if usage else max(len(raw_text) // 4, 1)
    )

    return _finalize_response(
        ModelResponse(
            text=raw_text,
            estimated_output_tokens=output_tokens,
            input_tokens=input_tokens,
            is_mock=False,
            latency_ms=round(latency_ms, 1),
            litellm_model=litellm_model,
            provider=resolved_provider,
        )
    )


def _generate_mock_response(model_id: str, context: PromptContext) -> ModelResponse:
    start = time.perf_counter()
    provider = _provider_for_model(model_id)

    base = _MOCK_TEMPLATES.get(context.task_type, _MOCK_TEMPLATES["general_qa"])
    text = (
        f"[Mock response — {provider} / {model_id}]\n\n"
        f"Task: {context.task_type}\n\n"
        f"{base}\n\n"
        f"---\n"
        f"Add an API key for {provider} under Model Controls → API Keys."
    )
    output_tokens = max(len(text) // 4, 1)
    latency_ms = (time.perf_counter() - start) * 1000

    return _finalize_response(
        ModelResponse(
            text=text,
            estimated_output_tokens=output_tokens,
            input_tokens=None,
            is_mock=True,
            latency_ms=round(latency_ms, 1),
            litellm_model="mock",
            provider=provider,
        )
    )


def _fake_stream_chunks(text: str) -> Iterator[str]:
    words = text.split()
    if not words:
        return
    for index, word in enumerate(words):
        yield word if index == 0 else f" {word}"


def _call_provider_stream(
    model_id: str,
    context: PromptContext,
    messages: list[dict] | None = None,
    *,
    api_key: str | None = None,
) -> Iterator[str]:
    import litellm

    litellm_model = to_litellm_model(model_id)
    litellm_messages = _build_litellm_messages(context, model_id, messages=messages)

    kwargs: dict = {
        "model": litellm_model,
        "messages": litellm_messages,
        "stream": True,
    }
    if api_key:
        kwargs["api_key"] = api_key
    response = litellm.completion(**kwargs)
    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def stream_response(
    groq_model: str,
    context: PromptContext,
    messages: list[dict] | None = None,
    *,
    db=None,
    user_id: int | None = None,
) -> Iterator[str]:
    """Yield response text chunks for SSE streaming."""
    model_id = groq_model
    provider = _provider_for_model(model_id)
    api_key = _resolve_api_key(db, user_id, provider)
    if not api_key:
        if not _allow_mock_fallback():
            raise MissingApiKeyError(provider)
        logger.info(
            "Mock stream fallback | model=%s | provider=%s | reason=no provider key",
            model_id,
            provider,
        )
        mock = _generate_mock_response(model_id, context)
        yield from _fake_stream_chunks(mock.text)
        return

    try:
        yield from _call_provider_stream(
            model_id, context, messages=messages, api_key=api_key
        )
        if db is not None and user_id is not None:
            from services.api_key_service import mark_provider_key_used

            mark_provider_key_used(db, user_id, provider)
    except MissingApiKeyError:
        raise
    except Exception as exc:
        logger.warning(
            "Stream failed | model=%s | provider=%s | error=%s — fake streaming mock",
            model_id,
            provider,
            exc,
        )
        if not _allow_mock_fallback():
            raise
        mock = _generate_mock_response(model_id, context)
        yield from _fake_stream_chunks(mock.text)


def build_response_from_stream(
    groq_model: str,
    context: PromptContext,
    accumulated_text: str,
    *,
    latency_ms: float,
    litellm_model: str = "",
    input_tokens: int | None = None,
    is_mock: bool = False,
    provider: str | None = None,
) -> ModelResponse:
    model_id = groq_model
    output_tokens = max(len(accumulated_text) // 4, 1)
    return _finalize_response(
        ModelResponse(
            text=accumulated_text,
            estimated_output_tokens=output_tokens,
            input_tokens=input_tokens,
            is_mock=is_mock,
            latency_ms=round(latency_ms, 1),
            litellm_model=litellm_model or to_litellm_model(model_id),
            provider=provider or _provider_for_model(model_id),
        )
    )


def generate_response(
    groq_model: str,
    context: PromptContext,
    messages: list[dict] | None = None,
    *,
    db=None,
    user_id: int | None = None,
) -> ModelResponse:
    """Main entry point — called after the router picks a model."""
    model_id = groq_model
    provider = _provider_for_model(model_id)
    api_key = _resolve_api_key(db, user_id, provider)
    if not api_key:
        if not _allow_mock_fallback():
            raise MissingApiKeyError(provider)
        logger.info(
            "Mock fallback | model=%s | provider=%s | reason=no provider key",
            model_id,
            provider,
        )
        return _generate_mock_response(model_id, context)

    try:
        result = _call_provider(
            model_id, context, messages=messages, api_key=api_key, provider=provider
        )
        if db is not None and user_id is not None:
            from services.api_key_service import mark_provider_key_used

            mark_provider_key_used(db, user_id, provider)
        logger.info(
            "LLM success | provider=%s | model=%s | input_tokens=%s | "
            "output_tokens=%s | latency_ms=%.1f",
            result.provider,
            result.litellm_model,
            result.input_tokens,
            result.estimated_output_tokens,
            result.latency_ms,
        )
        return result
    except MissingApiKeyError:
        raise
    except Exception as exc:
        logger.warning(
            "LLM call failed | model=%s | provider=%s | error=%s — using mock",
            model_id,
            provider,
            exc,
        )
        if not _allow_mock_fallback():
            raise
        return _generate_mock_response(model_id, context)
