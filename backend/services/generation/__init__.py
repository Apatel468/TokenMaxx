"""Pluggable generation services for documents and images."""

from services.generation.intent import GenerationIntent, detect_generation_intent

__all__ = ["GenerationIntent", "detect_generation_intent"]
