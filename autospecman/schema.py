"""Minimal schema helpers for AutoSpecMan specs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

SPEC_VERSION = "0.1.0"


def empty_spec(repo_path: Path) -> Dict[str, Any]:
    """Return a base spec dict that other modules can enrich."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "metadata": {
            "spec_version": SPEC_VERSION,
            "generated_at": timestamp,
            "repository": str(repo_path.resolve()),
        },
        "language_stack": [],
        "tooling": {
            "package_managers": [],
            "formatters": [],
            "linters": [],
            "test_frameworks": [],
            "ci_systems": [],
        },
        "workflow": {
            "commit_cadence_per_week": None,
            "active_contributors": None,
            "release_signal": None,
        },
        "quality_gates": {
            "required_checks": [],
            "security_tools": [],
        },
        "structure": {
            "top_level_patterns": [],
            "service_markers": [],
            "notable_directories": [],
        },
        "api_surface": {
            "openapi_files": [],
            "graphql_files": [],
            "route_files": [],
            "client_collections": [],
        },
        "data_assets": {
            "ddl_files": [],
            "migration_dirs": [],
            "orm_configs": [],
        },
        "confidence": {},
        "notes": [],
    }


def register_confidence(spec: Dict[str, Any], key: str, value: float) -> None:
    """Store a bounded confidence score for a specific spec section."""
    spec.setdefault("confidence", {})
    spec["confidence"][key] = max(0.0, min(1.0, value))

