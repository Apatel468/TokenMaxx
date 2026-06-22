"""
Generation intent detection — routes prompts to chat, document, or image flows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from services.generation.format_registry import (
    EXTENSION_KEYWORDS,
    IMAGE_TYPE_KEYWORDS,
    PROJECT_KEYWORDS,
    is_supported_extension,
)

Modality = Literal["chat", "document", "image"]


@dataclass
class GenerationIntent:
    """Detected generation modality and subtype."""

    modality: Modality = "chat"
    file_type: str | None = None
    image_type: str | None = None
    is_project: bool = False
    confidence: float = 0.0
    matched_keywords: list[str] | None = None


_DOCUMENT_ACTION_PATTERNS = [
    r"\b(create|generate|build|make|write|export|produce)\b.{0,40}\b(report|document|file|proposal|readme|spreadsheet|presentation)\b",
    r"\b(create|generate|build|make|write)\b.{0,30}\b(pdf|docx|pptx|xlsx|markdown|dockerfile|terraform)\b",
    r"\b(api documentation|openapi|swagger|graphql schema|postman collection)\b",
    r"\b(contributing\.md|changelog\.md|technical design|srs|tdd)\b",
]

_IMAGE_ACTION_PATTERNS = [
    r"\b(create|generate|design|draw|make)\b.{0,40}\b(image|diagram|mockup|flowchart|infographic|logo|illustration|wireframe)\b",
    r"\b(architecture diagram|system diagram|network diagram|dashboard mockup)\b",
]


def _normalize(prompt: str) -> str:
    return prompt.lower().strip()


def _detect_file_extension(normalized: str) -> str | None:
    for ext, keywords in EXTENSION_KEYWORDS.items():
        for kw in keywords:
            if kw in normalized:
                return ext

    # Explicit extension mention: "as a .py file", "format: json"
    ext_match = re.search(r"\.([a-z0-9]{1,10})\b", normalized)
    if ext_match:
        candidate = ext_match.group(1)
        if is_supported_extension(candidate):
            return candidate

    return None


def _detect_image_type(normalized: str) -> str | None:
    for image_type, keywords in IMAGE_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in normalized:
                return image_type
    return None


def _is_project_request(normalized: str) -> bool:
    if "zip" in normalized or "project structure" in normalized:
        return True
    return any(kw in normalized for kw in PROJECT_KEYWORDS)


def detect_generation_intent(prompt: str) -> GenerationIntent:
    """
    Classify whether a prompt requests chat, document file, or image generation.

    Document and image intents take priority over normal chat when confidence is high.
    """
    if not prompt or not prompt.strip():
        return GenerationIntent()

    normalized = _normalize(prompt)
    matched: list[str] = []

    # Image detection
    image_score = 0
    image_type = _detect_image_type(normalized)
    if image_type:
        image_score += 2
        matched.append(f"image:{image_type}")
    for pattern in _IMAGE_ACTION_PATTERNS:
        if re.search(pattern, normalized):
            image_score += 1
            matched.append("image:action")

    # Document detection
    doc_score = 0
    file_type = _detect_file_extension(normalized)
    if file_type:
        doc_score += 2
        matched.append(f"doc:{file_type}")
    for pattern in _DOCUMENT_ACTION_PATTERNS:
        if re.search(pattern, normalized):
            doc_score += 1
            matched.append("doc:action")

    is_project = _is_project_request(normalized)
    if is_project:
        doc_score += 2
        file_type = file_type or "zip"
        matched.append("doc:project")

    # Coding file creation without explicit "create" — lower confidence
    if file_type and doc_score == 2 and not is_project:
        if re.search(r"\b(create|generate|write|build|make|export)\b", normalized):
            doc_score += 1

    if image_score >= 2 and image_score >= doc_score:
        confidence = min(0.55 + image_score * 0.12, 0.98)
        return GenerationIntent(
            modality="image",
            image_type=image_type or "general",
            confidence=confidence,
            matched_keywords=matched,
        )

    if doc_score >= 2:
        confidence = min(0.55 + doc_score * 0.12, 0.98)
        return GenerationIntent(
            modality="document",
            file_type=file_type or "txt",
            is_project=is_project or file_type == "zip",
            confidence=confidence,
            matched_keywords=matched,
        )

    return GenerationIntent(modality="chat", confidence=0.0, matched_keywords=matched)
