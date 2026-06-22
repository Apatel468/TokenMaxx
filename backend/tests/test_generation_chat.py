"""Integration tests for document and image generation via chat API."""

import pytest

from tests.conftest import auth_headers


@pytest.fixture
def headers(auth_token):
    return auth_headers(auth_token)


def test_document_generation_chat(client, headers, monkeypatch, tmp_path):
    """POST /chat with document intent returns artifact metadata."""
    from services.generation.document_generator import DocumentGenerationResult
    from services.model_clients import ModelResponse

    mock_result = DocumentGenerationResult(
        content="# Report\n\nContent here",
        file_name="report.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        storage_path="/tmp/mock.pdf",
        file_size=1024,
        model_used="llama-3.1-8b-instant",
        provider="groq",
        model_response=ModelResponse(
            text="# Report\n\nContent",
            estimated_output_tokens=50,
            provider="groq",
        ),
    )

    def fake_generate(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "services.generation.document_generator.generate_document",
        fake_generate,
    )

    response = client.post(
        "/chat",
        json={"prompt": "Create a PDF report on sales", "enhance_prompt": False},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["modality"] == "document"
    assert body["generation_artifact"] is not None
    assert body["generation_artifact"]["artifact_type"] == "document"


def test_image_generation_chat(client, headers, monkeypatch):
    from services.generation.image_generator import ImageGenerationResult

    mock_result = ImageGenerationResult(
        storage_path="/tmp/mock.png",
        file_name="mock.png",
        image_type="flowchart",
        provider_used="openai",
        is_mock=True,
    )

    monkeypatch.setattr(
        "services.generation.image_generator.generate_image",
        lambda *a, **k: mock_result,
    )

    response = client.post(
        "/chat",
        json={"prompt": "Create a flowchart for user login", "enhance_prompt": False},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["modality"] == "image"
    assert body["generation_artifact"]["artifact_type"] == "image"


def test_generation_history_empty(client, headers):
    response = client.get("/generations/history", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "documents" in body
    assert "images" in body
