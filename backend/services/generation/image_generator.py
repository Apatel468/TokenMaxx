"""
Image generation — routes to OpenAI DALL-E via LiteLLM with mock fallback.
"""

from __future__ import annotations

import base64
import logging
import os
import time
import urllib.request
from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.api_key_service import resolve_api_key
from services.generation.storage import image_storage_path

logger = logging.getLogger(__name__)

DEFAULT_IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE = "1024x1024"


@dataclass
class ImageGenerationResult:
    """Result of image generation."""

    storage_path: str
    file_name: str
    mime_type: str = "image/png"
    width: int = 1024
    height: int = 1024
    provider_used: str = "openai"
    model_used: str = DEFAULT_IMAGE_MODEL
    image_type: str = "general"
    latency_ms: float = 0.0
    is_mock: bool = False
    revised_prompt: str = ""


def _allow_mock() -> bool:
    return os.getenv("ALLOW_MOCK_LLM", "true").lower() in ("1", "true", "yes")


def _generate_mock_image(path, prompt: str, image_type: str) -> ImageGenerationResult:
    """Create a simple placeholder PNG when no API key is available."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (1024, 1024), color=(30, 41, 59))
        draw = ImageDraw.Draw(img)
        draw.rectangle([40, 40, 984, 984], outline=(99, 102, 241), width=4)
        lines = [
            "TokenMaxx — Mock Image",
            f"Type: {image_type}",
            prompt[:80] + ("…" if len(prompt) > 80 else ""),
        ]
        y = 400
        for line in lines:
            draw.text((80, y), line, fill=(226, 232, 240))
            y += 40
        img.save(str(path), format="PNG")
    except ImportError:
        # Minimal valid 1x1 PNG if Pillow unavailable
        path.write_bytes(
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
            )
        )

    return ImageGenerationResult(
        storage_path=str(path),
        file_name=path.name,
        image_type=image_type,
        is_mock=True,
        revised_prompt=prompt,
    )


def _download_url_to_file(url: str, path) -> None:
    with urllib.request.urlopen(url, timeout=120) as resp:
        path.write_bytes(resp.read())


def generate_image(
    prompt: str,
    *,
    image_type: str = "general",
    db: Session | None = None,
    user_id: int | None = None,
    model: str = DEFAULT_IMAGE_MODEL,
) -> ImageGenerationResult:
    """Generate an image and save to user storage."""
    start = time.perf_counter()
    path = image_storage_path(user_id or 0, "png")

    api_key = None
    if db is not None and user_id is not None:
        api_key = resolve_api_key(db, user_id, "openai")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "").strip() or None

    if not api_key:
        if _allow_mock():
            result = _generate_mock_image(path, prompt, image_type)
            result.latency_ms = round((time.perf_counter() - start) * 1000, 1)
            return result
        raise RuntimeError(
            "No OpenAI API key configured for image generation. "
            "Add OPENAI_API_KEY or a user OpenAI key under API Keys."
        )

    import litellm

    type_hint = image_type.replace("_", " ")
    full_prompt = f"{prompt}\n\nStyle: professional {type_hint}, clean layout, high quality."

    try:
        response = litellm.image_generation(
            model=model,
            prompt=full_prompt,
            api_key=api_key,
            size=IMAGE_SIZE,
            n=1,
        )
    except Exception as exc:
        logger.warning("Image generation failed (%s) — using mock", exc)
        if _allow_mock():
            result = _generate_mock_image(path, prompt, image_type)
            result.latency_ms = round((time.perf_counter() - start) * 1000, 1)
            return result
        raise

    data = response.data[0] if response.data else None
    if not data:
        raise RuntimeError("Image provider returned no data.")

    revised = getattr(data, "revised_prompt", None) or prompt

    if getattr(data, "b64_json", None):
        path.write_bytes(base64.b64decode(data.b64_json))
    elif getattr(data, "url", None):
        _download_url_to_file(data.url, path)
    else:
        raise RuntimeError("Image provider returned no url or b64_json.")

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    w, h = 1024, 1024
    if "x" in IMAGE_SIZE:
        parts = IMAGE_SIZE.split("x")
        w, h = int(parts[0]), int(parts[1])

    return ImageGenerationResult(
        storage_path=str(path),
        file_name=path.name,
        width=w,
        height=h,
        provider_used="openai",
        model_used=model,
        image_type=image_type,
        latency_ms=latency_ms,
        is_mock=False,
        revised_prompt=revised,
    )
