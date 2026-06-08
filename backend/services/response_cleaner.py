"""
Response Cleaner — strip internal reasoning from model output before storage/API.

Some models (e.g. Qwen) may emit <think> blocks or leave them unclosed.
This module removes that content so users only see the final answer.
"""

import re

# Tags models use for hidden chain-of-thought (matched case-insensitively)
_OPEN_TAG = re.compile(r"<think>", re.IGNORECASE)
_CLOSE_TAG = re.compile(r"</think>", re.IGNORECASE)
_COMPLETE_BLOCK = re.compile(
    r"<think>.*?</think>",
    re.DOTALL | re.IGNORECASE,
)

# Heuristics for finding the "final answer" when a closing tag is missing
_CODE_FENCE = re.compile(r"```", re.MULTILINE)
_ANSWER_START = re.compile(
    r"(?:^|\n\n+)"
    r"(?:"
    r"#{1,3}\s+|"  # markdown heading
    r"\*\*[^*]+\*\*\s*|"
    r"(?:Here(?:'s| is)|The (?:solution|answer|code|result)|Final answer:)|"
    r"```"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def _strip_after_unclosed_thinking(remainder: str) -> str:
    """
    When </think> is missing, try to keep only the final answer.

    Priority:
      1. First markdown code fence (```)
      2. First answer-like heading or phrase
      3. Last non-empty paragraph (often the conclusion after rambling)
    """
    text = remainder.strip()
    if not text:
        return ""

    # Prefer content starting at the first code block
    fence = _CODE_FENCE.search(text)
    if fence:
        return text[fence.start() :].strip()

    # Look for a clear answer section after blank lines
    answer = _ANSWER_START.search(text)
    if answer:
        start = answer.start()
        if text[start] == "\n":
            start = start + 1
        return text[start:].strip()

    # Fall back: drop the first paragraph (often pure reasoning) and keep the rest
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) > 1:
        return "\n\n".join(paragraphs[1:]).strip()
    if paragraphs:
        return paragraphs[0]

    return text


def clean_model_response(text: str) -> str:
    """
    Remove <think>...</think> blocks from model text.

    If a closing tag is missing, remove everything before the first likely
    final answer or code block when possible.

    Args:
        text: Raw model completion string.

    Returns:
        Cleaned text safe to return to the frontend and save in the database.
    """
    if not text or not text.strip():
        return text

    cleaned = text

    # Remove all complete thinking blocks (repeat in case of multiples)
    while True:
        updated = _COMPLETE_BLOCK.sub("", cleaned)
        if updated == cleaned:
            break
        cleaned = updated

    # Handle unclosed <think> (no matching close tag)
    open_match = _OPEN_TAG.search(cleaned)
    if open_match:
        before = cleaned[: open_match.start()]
        after = cleaned[open_match.end() :]
        recovered = _strip_after_unclosed_thinking(after)
        cleaned = f"{before}{recovered}".strip()

    # Remove any stray tags left in the output
    cleaned = _OPEN_TAG.sub("", cleaned)
    cleaned = _CLOSE_TAG.sub("", cleaned)

    # Collapse extra blank lines left after removals
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    return cleaned
