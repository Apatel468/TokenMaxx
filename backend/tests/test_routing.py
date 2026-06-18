"""
Tests for task-aware model routing scores.
"""

from services.groq_models import get_routable_models
from services.model_scorer import pick_best_model, score_candidates


def _winner(task_type: str, prompt: str) -> str:
    catalog = get_routable_models()
    winner, _ = pick_best_model(task_type, catalog, prompt=prompt)
    assert winner is not None
    return winner.model_id


def test_general_qa_short_prompt_prefers_fast_cheap_model():
    winner = _winner("general_qa", "What is photosynthesis?")
    assert winner == "llama-3.1-8b-instant"


def test_coding_prompt_prefers_qwen():
    winner = _winner(
        "coding",
        "Debug this React component that throws a hooks error on re-render.",
    )
    assert winner == "qwen/qwen3-32b"


def test_report_prompt_prefers_quality_writing_model():
    winner = _winner(
        "report",
        "Write a professional business report on Q3 revenue trends for executives.",
    )
    assert winner in {
        "llama-3.3-70b-versatile",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "claude-3-5-sonnet",
        "gpt-4o",
    }


def test_complex_reasoning_prefers_high_reasoning_model():
    winner = _winner(
        "reasoning",
        "Solve this complex logic puzzle step by step and prove your answer.",
    )
    assert winner in {
        "openai/gpt-oss-120b",
        "o3-mini",
        "gpt-4o",
        "claude-3-5-sonnet",
    }


def test_summarization_does_not_default_to_gpt_oss_20b():
    winner = _winner(
        "summarization",
        "Summarize this paragraph in three bullet points.",
    )
    assert winner != "openai/gpt-oss-20b"


def test_different_tasks_pick_different_models():
    winners = {
        _winner("general_qa", "What is DNA?"),
        _winner("coding", "Implement a binary search in Python."),
        _winner("reasoning", "Analyze this multi-step logic puzzle."),
    }
    assert len(winners) >= 2


def test_top_scores_returned_in_metadata():
    catalog = get_routable_models()
    scored = score_candidates(
        "math",
        catalog,
        prompt="Solve the integral of x^2 dx step by step.",
    )
    assert len(scored) >= 3
    assert scored[0].model_id == "qwen/qwen3-32b"
    assert scored[0].score >= scored[1].score
    assert scored[0].task_preference_bonus > 0
