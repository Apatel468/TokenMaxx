"""
Config Loader — reads routing config from config/models.yaml.

Task profiles and auxiliary model ids live here.
Per-model pricing and capability scores live in config/model_registry.py.
"""

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "models.yaml"
_config_cache: dict | None = None


def load_models_config() -> dict:
    """Load and cache config/models.yaml."""
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def resolve_task_key(task_type: str) -> str:
    """Map analyzer task_type to a task_profiles key in models.yaml."""
    config = load_models_config()
    profiles = config.get("task_profiles", {})
    if task_type in profiles:
        return task_type
    aliases = config.get("task_aliases", {})
    alias = aliases.get(task_type)
    if alias and alias in profiles:
        return alias
    return config.get("default_task", "general_qa")


def get_task_profile(task_type: str) -> dict:
    """Return the task profile dict (description + task_match_weights)."""
    config = load_models_config()
    key = resolve_task_key(task_type)
    profiles = config.get("task_profiles", {})
    return profiles.get(key, profiles.get(config.get("default_task", "general_qa"), {}))


def get_scoring_weights(task_type: str, complexity: float) -> dict[str, float]:
    """
    Return composite score weights for a task.

    Business/report profiles use fixed quality-first weights; other tasks shift
    with prompt complexity (cheap models win simple prompts).
    """
    profile = get_task_profile(task_type)
    custom = profile.get("scoring_weights")
    if custom:
        return {
            "task": float(custom.get("task", 0.45)),
            "reasoning": float(custom.get("reasoning", 0.25)),
            "writing": float(custom.get("writing", 0.20)),
            "cost": float(custom.get("cost", 0.05)),
            "speed": float(custom.get("speed", 0.05)),
        }

    if complexity < 0.35:
        return {"task": 0.42, "reasoning": 0.12, "writing": 0.0, "cost": 0.12, "speed": 0.16}
    if complexity > 0.65:
        return {"task": 0.50, "reasoning": 0.30, "writing": 0.0, "cost": 0.04, "speed": 0.08}
    return {"task": 0.46, "reasoning": 0.22, "writing": 0.0, "cost": 0.08, "speed": 0.12}


def get_auxiliary_model(role: str) -> str:
    """
    Return a small Groq model id for non-routing calls.

    role: classifier | enhancer | title
    """
    config = load_models_config()
    auxiliary = config.get("auxiliary", {})
    return auxiliary.get(role, "llama-3.1-8b-instant")


def get_premium_baseline() -> dict:
    """Return premium baseline used for savings % calculation."""
    return load_models_config().get("premium_baseline", {})


def get_allowed_task_types() -> list[str]:
    """Task type keys the classifier may choose (task_profiles keys)."""
    config = load_models_config()
    return list(config.get("task_profiles", {}).keys())


def get_default_task_type() -> str:
    """Fallback task type when classification is uncertain."""
    return load_models_config().get("default_task", "general_qa")


def get_classifier_task_types() -> list[str]:
    """Task types the LLM classifier may return."""
    from services.llm_classifier import SUPPORTED_TASK_TYPES

    return sorted(SUPPORTED_TASK_TYPES)


def get_classifier_config() -> dict:
    """Groq model used for LLM-based prompt classification."""
    model_id = get_auxiliary_model("classifier")
    return {"provider": "groq", "model": model_id}
