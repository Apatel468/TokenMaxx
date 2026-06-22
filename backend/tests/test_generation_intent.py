"""Tests for generation intent detection."""

from services.generation.intent import detect_generation_intent


def test_detect_document_pdf_intent():
    intent = detect_generation_intent("Create a PDF report on Q3 revenue")
    assert intent.modality == "document"
    assert intent.file_type == "pdf"
    assert intent.confidence > 0.5


def test_detect_document_readme_intent():
    intent = detect_generation_intent("Generate a README file for my FastAPI project")
    assert intent.modality == "document"
    assert intent.file_type in ("md", "txt", "zip")


def test_detect_project_zip_intent():
    intent = detect_generation_intent("Build a complete Flask API project structure as a zip")
    assert intent.modality == "document"
    assert intent.is_project is True


def test_detect_image_diagram_intent():
    intent = detect_generation_intent("Create an architecture diagram for a microservices system")
    assert intent.modality == "image"
    assert intent.image_type == "architecture_diagram"


def test_detect_image_logo_intent():
    intent = detect_generation_intent("Generate a logo for my startup")
    assert intent.modality == "image"
    assert intent.image_type == "logo"


def test_chat_intent_for_general_qa():
    intent = detect_generation_intent("What is photosynthesis?")
    assert intent.modality == "chat"


def test_detect_python_file_intent():
    intent = detect_generation_intent("Create a Python file with a FastAPI hello world endpoint")
    assert intent.modality == "document"
    assert intent.file_type == "py"
