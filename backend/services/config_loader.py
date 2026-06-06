"""
Config Loader — reads routing rules from config/models.yaml.

The YAML file defines which Groq model to use for each task type.
Change models.yaml to update routing without editing Python code.
"""

from pathlib import Path

import yaml

# Path to models.yaml (backend/config/models.yaml)
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "models.yaml"

# Cached config so we only read the file once per server run
_config_cache: dict | None = None

# Map analyzer task types that aren't in YAML to a YAML key
_TASK_ALIASES: dict[str, str] = {
    "summarization": "report",
    "creative_writing": "report",
    "data_analysis": "report",
    "translation": "general_qa",
}


def load_models_config() -> dict:
    """Load and cache config/models.yaml."""
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def get_route_for_task(task_type: str) -> dict:
    """
    Return the routing entry for a task type.

    Looks up task_type in models.yaml. If not found, uses aliases
    (e.g. summarization → report) or falls back to default_task.
    """
    config = load_models_config()
    models = config["models"]

    # Direct match in YAML
    if task_type in models:
        return models[task_type]

    # Try alias (e.g. summarization → report)
    alias = _TASK_ALIASES.get(task_type)
    if alias and alias in models:
        return models[alias]

    # Fall back to default_task from YAML
    default_key = config.get("default_task", "general_qa")
    return models[default_key]


def get_pricing() -> dict:
    """Return Groq model pricing block from YAML."""
    return load_models_config().get("pricing", {})


def get_premium_baseline() -> dict:
    """Return premium baseline used for savings % calculation."""
    return load_models_config().get("premium_baseline", {})


def get_allowed_task_types() -> list[str]:
    """
    Return task type keys the LLM classifier is allowed to choose.

    These are the top-level keys under "models" in models.yaml.
    """
    config = load_models_config()
    return list(config["models"].keys())


def get_default_task_type() -> str:
    """Return the fallback task type when classification is uncertain."""
    return load_models_config().get("default_task", "general_qa")


def get_classifier_config() -> dict:
    """
    Return the Groq model used for LLM-based prompt classification.

    Falls back to general_qa's model if "classifier" is missing from YAML.
    """
    config = load_models_config()
    if "classifier" in config:
        return config["classifier"]
    default_key = config.get("default_task", "general_qa")
    return config["models"][default_key]
