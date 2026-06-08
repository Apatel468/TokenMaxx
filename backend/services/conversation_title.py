"""
Conversation Title — ChatGPT-style titles after the first assistant reply.

Uses the first user message AND first assistant response to name the thread.
Primary: Groq via LiteLLM. Fallback: rule-based noun phrases.

Generated once when the first reply is saved and stored in the database.
"""

import json
import logging
import os
import re

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_ENV_KEY = "GROQ_API_KEY"
TITLE_MODEL = "llama-3.1-8b-instant"
MIN_WORDS = 3
MAX_WORDS = 8
MAX_PROMPT_CHARS = 800

_BANNED_PREFIXES = (
    "questions and answers about",
    "discussion of",
    "discussion about",
    "information regarding",
    "guide to",
)

_SKIP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "to", "for", "of", "in", "on", "at",
    "is", "are", "was", "were", "be", "been", "being", "me", "my", "i", "you",
    "your", "please", "can", "could", "would", "will", "help", "give", "need",
    "want", "show", "tell", "write", "create", "make", "build", "generate",
    "do", "does", "did", "that", "this", "with", "from", "as", "it", "its",
})


def _has_groq_key() -> bool:
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def _to_litellm_model(model: str) -> str:
    if model.startswith("groq/"):
        return model
    return f"groq/{model}"


def _word_count(text: str) -> int:
    return len(re.sub(r"[?!.]+$", "", text.strip()).split())


def _has_banned_prefix(title: str) -> bool:
    lower = title.lower().strip()
    return any(lower.startswith(prefix) for prefix in _BANNED_PREFIXES)


def _is_valid_title(title: str) -> bool:
    if not title or not title.strip():
        return False
    cleaned = title.strip()
    if cleaned.endswith("...") or cleaned.endswith("…"):
        return False
    if cleaned.endswith((",", ";", ":", "-", "—")):
        return False
    if _has_banned_prefix(cleaned):
        return False
    words = _word_count(cleaned)
    if words < MIN_WORDS or words > MAX_WORDS:
        return False
    return True


def _normalize_title(title: str) -> str:
    cleaned = title.strip().strip("\"'")
    cleaned = cleaned.splitlines()[0].strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned.endswith("?"):
        cleaned = cleaned.rstrip("?").strip()
        cleaned = re.sub(r"[.!…]+$", "", cleaned).strip()
        if cleaned:
            cleaned = f"{cleaned}?"
    else:
        cleaned = re.sub(r"[.?!…]+$", "", cleaned).strip()
    return cleaned


def _fit_word_range(title: str, min_words: int = MIN_WORDS, max_words: int = MAX_WORDS) -> str:
    has_q = title.rstrip().endswith("?")
    core = title.rstrip("?").strip()
    words = core.split()
    if len(words) > max_words:
        words = words[:max_words]
    result = " ".join(words)
    if has_q and result:
        result = f"{result}?"
    return result


def _truncate(text: str, max_chars: int = MAX_PROMPT_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _extract_json_title(text: str) -> str:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    parsed = json.loads(cleaned)
    return str(parsed.get("title", "")).strip()


def _format_turn_context(user_message: str, assistant_response: str) -> str:
    return (
        f"User:\n{_truncate(user_message)}\n\n"
        f"Assistant:\n{_truncate(assistant_response)}"
    )


def _generate_title_with_ai(user_message: str, assistant_response: str) -> str | None:
    """Call Groq to produce a ChatGPT-style title from the first exchange."""
    import litellm

    system_prompt = f"""Generate a conversation title based on the first user message and assistant response.

Requirements:
- {MIN_WORDS} to {MAX_WORDS} words
- Sound like a ChatGPT conversation title
- Describe the actual conversation topic (use both messages)
- Use natural English with proper grammar — a complete thought
- Do not use filler words
- Do NOT start with:
  "Questions and Answers About"
  "Discussion of"
  "Information Regarding"
  "Guide to"
- Prefer noun phrases or concise questions
- Do NOT copy either message verbatim
- NEVER end with "..." or cut off mid-sentence
- Return title only in JSON

Respond with JSON only:
{{"title": "<title text>"}}

Examples:

User:
Who is going to win the F1 championship this year?

Assistant:
Analysis of drivers, teams, odds, and predictions.

{{"title": "2026 F1 Championship Predictions"}}

User:
Give me a Python calculator script

Assistant:
Provides calculator code with error handling.

{{"title": "Python Calculator with Error Handling"}}

User:
Generate flashcards about database normalization

Assistant:
Creates study flashcards.

{{"title": "Database Normalization Flashcards"}}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _format_turn_context(user_message, assistant_response)},
    ]
    litellm_model = _to_litellm_model(TITLE_MODEL)

    try:
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception:
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            temperature=0,
        )

    raw = response.choices[0].message.content or ""
    if not raw.strip():
        return None

    title = _normalize_title(_extract_json_title(raw))
    title = _fit_word_range(title)

    if _is_valid_title(title):
        return title
    return None


def _detect_year(*texts: str) -> str | None:
    for text in texts:
        match = re.search(r"\b(20\d{2})\b", text)
        if match:
            return match.group(1)
    return None


def _build_topic_title(user_message: str, assistant_response: str) -> str:
    """Rule-based fallback using both sides of the first exchange."""
    user = user_message.strip().splitlines()[0].strip()
    asst = assistant_response.strip()
    user_lower = user.lower()
    asst_lower = asst.lower()
    combined = f"{user_lower} {asst_lower}"

    if any(w in combined for w in ("f1", "formula 1", "formula one")) or (
        "championship" in user_lower and any(w in combined for w in ("driver", "race", "grand prix"))
    ):
        year = _detect_year(user, asst) or ""
        base = "F1 Championship Predictions"
        title = f"{year} {base}".strip() if year else base
        return _fit_word_range(title)

    if "flashcard" in user_lower:
        if "normalization" in user_lower or "normalisation" in user_lower:
            return "Database Normalization Flashcards"
        if "database" in user_lower:
            return "Database Concepts Flashcards"
        return "Study Flashcards"

    if "python" in user_lower and any(w in user_lower for w in ("calculator", "calc")):
        if any(w in asst_lower for w in ("error", "handling", "try", "except", "validation")):
            return "Python Calculator with Error Handling"
        return "Python Calculator Script"

    if "prime" in user_lower and "number" in user_lower:
        return "Prime Number Check in Python" if "python" in user_lower else "Prime Number Check"

    if "python" in user_lower:
        return "Python Code Help"

    if "database" in user_lower or "sql" in user_lower:
        return "Database Query Help"

    if "summar" in user_lower:
        return "Article Summary"

    if "report" in user_lower:
        return "Professional Report Draft"

    words = re.sub(r"[^\w\s'-]", " ", user_lower).split()
    keywords = [w for w in words if w not in _SKIP_WORDS and len(w) > 2]
    if keywords:
        phrase = " ".join(w.capitalize() for w in keywords[:MAX_WORDS])
        return _fit_word_range(phrase)

    return "New Chat"


def generate_conversation_title(
    user_message: str,
    assistant_response: str,
    *,
    use_ai: bool = True,
) -> str:
    """
    Generate a title from the first user message and first assistant response.

    Requires both messages. Stored once per conversation; never regenerated if set.
    Set use_ai=False for fast backfill (rule-based only).
    """
    if not user_message or not user_message.strip():
        return "New Chat"
    if not assistant_response or not assistant_response.strip():
        return "New Chat"

    if use_ai and _has_groq_key():
        try:
            ai_title = _generate_title_with_ai(user_message, assistant_response)
            if ai_title:
                logger.info("AI conversation title | %s", ai_title)
                return ai_title
        except Exception as exc:
            logger.warning("AI title generation failed (%s) — using fallback", exc)

    fallback = _build_topic_title(user_message, assistant_response)
    logger.info("Fallback conversation title | %s", fallback)
    return fallback
