"""
Central routing for analysis profiles and task-specific model selection.
"""

from copy import deepcopy


DEFAULT_PROFILE = "fast"

TASK_MODELS = {
    "ai_logic": "meta/llama-3.1-70b-instruct",
    "ai_manual_testing": "meta/llama-3.1-70b-instruct",
    "ai_assessment": "meta/llama-3.1-70b-instruct",
    "static_fallback": "meta/llama-3.1-70b-instruct",
    "execution_fallback": "meta/llama-3.1-8b-instruct",
    "legacy_testing": "meta/llama-3.1-70b-instruct",
    "whitebox": "meta/llama-3.1-70b-instruct",
    "blackbox": "meta/llama-3.1-70b-instruct",
    "security": "meta/llama-3.1-70b-instruct",
    "performance_fallback": "meta/llama-3.1-8b-instruct",
}

PROFILE_SETTINGS = {
    "fast": {
        "include_execution": True,
        "include_static": True,
        "include_whitebox": True,
        "include_blackbox": False,
        "include_legacy_testing": False,
        "include_security": True,
        "include_performance": True,
        "include_ai": True,
        "include_regression": False,
        "ai_logic": True,
        "ai_manual_testing": False,
        "ai_assessment": True,
        "project_char_limit": 80000,
        "project_file_limit": 40,
    },
    "balanced": {
        "include_execution": True,
        "include_static": True,
        "include_whitebox": True,
        "include_blackbox": True,
        "include_legacy_testing": False,
        "include_security": True,
        "include_performance": True,
        "include_ai": True,
        "include_regression": False,
        "ai_logic": True,
        "ai_manual_testing": True,
        "ai_assessment": True,
        "project_char_limit": 140000,
        "project_file_limit": 80,
    },
    "deep": {
        "include_execution": True,
        "include_static": True,
        "include_whitebox": True,
        "include_blackbox": True,
        "include_legacy_testing": True,
        "include_security": True,
        "include_performance": True,
        "include_ai": True,
        "include_regression": True,
        "ai_logic": True,
        "ai_manual_testing": True,
        "ai_assessment": True,
        "project_char_limit": 200000,
        "project_file_limit": 120,
    },
}


def normalize_profile(value: str | None) -> str:
    """Return a supported profile name."""
    if not value:
        return DEFAULT_PROFILE
    value = str(value).strip().lower()
    return value if value in PROFILE_SETTINGS else DEFAULT_PROFILE


def get_profile_settings(profile: str | None) -> dict:
    """Return a mutable copy of the selected profile settings."""
    return deepcopy(PROFILE_SETTINGS[normalize_profile(profile)])


def get_task_model(task_name: str, default: str = "") -> str:
    """Return the preferred model for a task."""
    return TASK_MODELS.get(task_name, default)
