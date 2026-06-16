"""
Tests for Prompt Intelligence Engine v2.
"""

from services.prompt_intelligence import (
    analyze_and_enhance,
    format_enhanced_prompt_for_display,
    compute_complexity_score,
    complexity_level_from_score,
    normalize_task_type,
    sanitize_enhanced_prompt,
)


def test_simple_general_qa_gets_minimal_enhancement():
    analysis = analyze_and_enhance(
        "What is DNA?",
        task_type="general_qa",
        difficulty="easy",
    )

    assert analysis.complexity_level == "simple"
    assert analysis.complexity_score <= 33
    assert analysis.persona == "Helpful Expert"
    assert analysis.enhancement_strategy == "minimal_clarity"
    assert analysis.enhanced_prompt.strip() == "What is DNA?"


def test_coding_prompt_gets_engineer_persona_and_structure():
    analysis = analyze_and_enhance(
        "Write a Python function to check if a number is prime.",
        task_type="coding",
        difficulty="medium",
    )

    assert analysis.task_type == "coding"
    assert analysis.persona == "Senior Software Engineer"
    assert analysis.complexity_level in {"medium", "complex"}
    if analysis.complexity_level == "medium":
        assert "output format" in analysis.enhanced_prompt.lower()


def test_business_report_prompt_maps_to_business_persona():
    analysis = analyze_and_enhance(
        "Write a professional business report on Q3 revenue trends for executives.",
        task_type="report",
        difficulty="hard",
    )

    assert analysis.task_type == "business"
    assert analysis.persona == "Business Consultant"
    assert "executive" in analysis.output_format.lower() or "recommendations" in (
        analysis.output_format.lower()
    )
    assert analysis.complexity_level in {"medium", "complex"}
    if analysis.complexity_level == "complex":
        assert "step-by-step" in analysis.enhanced_prompt.lower() or "Requirements:" in (
            analysis.enhanced_prompt
        )


def test_complex_prompt_adds_full_specification_requirements():
    score = compute_complexity_score(
        "Analyze this architecture step by step, state assumptions, and compare trade-offs.",
        "reasoning",
        difficulty="hard",
    )
    assert complexity_level_from_score(score) == "complex"

    analysis = analyze_and_enhance(
        "Analyze this architecture step by step, state assumptions, and compare trade-offs.",
        task_type="reasoning",
        difficulty="hard",
    )

    assert analysis.enhancement_strategy.startswith("full_specification")
    assert "assumptions" in analysis.enhanced_prompt.lower()
    assert "output format" in analysis.enhanced_prompt.lower()


def test_enhanced_prompt_has_no_internal_notes():
    dirty = (
        "Summarize this article.\n\n"
        "[Original user request — preserve this intent: Summarize this article.]"
    )
    cleaned = sanitize_enhanced_prompt(dirty)
    assert "[Original user request" not in cleaned
    assert cleaned == "Summarize this article."

    analysis = analyze_and_enhance(
        "User request (preserve this intent exactly):\nExplain photosynthesis.",
        task_type="education",
        difficulty="easy",
    )
    displayed = format_enhanced_prompt_for_display(analysis.enhanced_prompt)
    assert "[Original user request" not in displayed
    assert "preserve this intent" not in displayed.lower()


def test_normalize_task_type_maps_report_to_business():
    assert normalize_task_type("report") == "business"
    assert normalize_task_type("math") == "reasoning"
    assert normalize_task_type("flashcards") == "education"
