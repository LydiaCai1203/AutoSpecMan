"""Detector utilities for AutoSpecMan."""

from .language import detect_languages, summarize_language_usage  # noqa: F401
from .tooling import (
    detect_ci_systems,
    detect_formatters,
    detect_linters,
    detect_package_managers,
    detect_security_tools,
    detect_test_frameworks,
)  # noqa: F401
from .history import analyze_git_history  # noqa: F401
from .structure import (  # noqa: F401
    analyze_directory_layout,
    detect_api_artifacts,
    detect_data_artifacts,
)
from .error_handling import detect_error_handling  # noqa: F401

__all__ = [
    "detect_languages",
    "summarize_language_usage",
    "detect_package_managers",
    "detect_formatters",
    "detect_linters",
    "detect_test_frameworks",
    "detect_ci_systems",
    "detect_security_tools",
    "analyze_git_history",
    "analyze_directory_layout",
    "detect_api_artifacts",
    "detect_data_artifacts",
    "detect_error_handling",
]

