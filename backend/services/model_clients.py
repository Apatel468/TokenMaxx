"""
Model Clients — mock AI model responses.

No real API keys needed. Each "model" returns a canned-style reply
that mentions which model answered and what task type was detected.

Later, replace these mocks with LiteLLM calls to real providers.
"""

from dataclasses import dataclass

from services.context_builder import PromptContext


@dataclass
class ModelResponse:
    """What we get back from a model (mock or real)."""

    text: str
    estimated_output_tokens: int


# Template responses keyed by task type — keeps mocks feel realistic
_RESPONSE_TEMPLATES: dict[str, str] = {
    "coding": (
        "Here's a starter approach for your coding request:\n\n"
        "```python\n"
        "def solve():\n"
        "    # Step 1: break the problem into smaller pieces\n"
        "    pass\n"
        "```\n\n"
        "I'd recommend testing edge cases and adding error handling next."
    ),
    "summarization": (
        "Summary:\n"
        "• Main point one from your text\n"
        "• Main point two\n"
        "• Key takeaway in one sentence"
    ),
    "creative_writing": (
        "Here is a creative draft based on your prompt:\n\n"
        "The morning light crept through the window, carrying with it "
        "the quiet promise of a story waiting to be told..."
    ),
    "data_analysis": (
        "Analysis overview:\n"
        "1. Data shape and quality look reasonable for basic stats.\n"
        "2. Consider grouping by category to spot trends.\n"
        "3. A simple chart (bar or line) would make patterns clearer."
    ),
    "translation": (
        "[Translated text would appear here]\n\n"
        "Note: For production, use a model fine-tuned on the target language."
    ),
    "general_qa": (
        "Here is a concise answer to your question:\n\n"
        "The short version is that this depends on context, but the "
        "core idea is straightforward once you break it into parts."
    ),
}


def generate_mock_response(model_id: str, context: PromptContext) -> ModelResponse:
    """
    Pretend to call an AI model and return a mock answer.

    Args:
        model_id: Which model "answered" (e.g. "gpt-4o-mini").
        context:  Prompt metadata from the context builder.

    Returns:
        ModelResponse with text and estimated output token count.
    """
    base_text = _RESPONSE_TEMPLATES.get(
        context.task_type,
        _RESPONSE_TEMPLATES["general_qa"],
    )

    # Wrap the template so it's obvious this is a mock
    full_response = (
        f"[Mock response from {model_id}]\n\n"
        f"Task detected: {context.task_type}\n\n"
        f"{base_text}\n\n"
        f"---\n"
        f"(In production, this would be a real LLM completion for: "
        f'"{context.prompt[:80]}{"..." if len(context.prompt) > 80 else ""}")'
    )

    output_tokens = max(len(full_response) // 4, 1)

    return ModelResponse(
        text=full_response,
        estimated_output_tokens=output_tokens,
    )
