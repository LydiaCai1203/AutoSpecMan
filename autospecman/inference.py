"""High-level orchestration for spec inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from . import repository
from .detectors import (
    analyze_directory_layout,
    analyze_git_history,
    detect_api_artifacts,
    detect_ci_systems,
    detect_data_artifacts,
    detect_formatters,
    detect_languages,
    detect_linters,
    detect_package_managers,
    detect_security_tools,
    detect_test_frameworks,
    summarize_language_usage,
)
from .schema import empty_spec, register_confidence

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


def infer_spec(
    repo_path: str | Path,
    max_commits: int = 400,
    use_llm: bool = True,
    llm_provider: str = "openai",
    llm_model: str = "gpt-3.5-turbo",
    llm_api_key: Optional[str] = None,
    llm_api_base_url: Optional[str] = None,
) -> Dict[str, Any]:
    root = Path(repo_path).resolve()
    ctx = repository.RepoContext.from_root(root)
    spec = empty_spec(root)

    languages = detect_languages(ctx.files)
    spec["language_stack"] = summarize_language_usage(languages)
    register_confidence(spec, "language_stack", 0.2 + 0.6 * bool(languages))

    managers = detect_package_managers(root)
    spec["tooling"]["package_managers"] = managers
    register_confidence(spec, "tooling.package_managers", 0.3 + 0.5 * bool(managers))

    formatters = detect_formatters(root)
    spec["tooling"]["formatters"] = formatters
    linters = detect_linters(root)
    spec["tooling"]["linters"] = linters
    tests = detect_test_frameworks(root)
    spec["tooling"]["test_frameworks"] = tests
    ci_systems = detect_ci_systems(root)
    spec["tooling"]["ci_systems"] = ci_systems
    security = detect_security_tools(root)
    spec["quality_gates"]["security_tools"] = security

    register_confidence(spec, "tooling.linters", 0.3 + 0.5 * bool(linters))
    register_confidence(spec, "tooling.formatters", 0.3 + 0.5 * bool(formatters))
    register_confidence(spec, "tooling.test_frameworks", 0.3 + 0.5 * bool(tests))
    register_confidence(spec, "tooling.ci_systems", 0.2 + 0.6 * bool(ci_systems))

    history = analyze_git_history(
        root,
        max_commits=max_commits,
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_api_base_url=llm_api_base_url,
    )
    spec["workflow"]["commit_cadence_per_week"] = history.average_commits_per_week
    spec["workflow"]["active_contributors"] = history.active_contributors
    spec["workflow"]["release_signal"] = history.recent_release_signal
    spec["workflow"]["branch_strategy"] = history.branch_strategy
    spec["workflow"]["branch_types"] = history.branch_types
    spec["workflow"]["commit_convention"] = history.commit_convention
    spec["workflow"]["branch_naming_pattern"] = history.branch_naming_pattern
    spec["workflow"]["tag_naming_convention"] = history.tag_naming_convention
    spec["workflow"]["recent_tags_count"] = history.recent_tags_count
    register_confidence(
        spec,
        "workflow.history",
        0.2
        + 0.6
        * bool(
            history.average_commits_per_week
            or history.branch_strategy
            or history.commit_convention
            or history.branch_naming_pattern
        ),
    )

    if ci_systems:
        spec["quality_gates"]["required_checks"] = [
            f"{system}-default" for system in ci_systems
        ]

    layout = analyze_directory_layout(ctx.root, ctx.directories)
    spec["structure"].update(layout)
    register_confidence(spec, "structure", 0.3 + 0.5 * bool(layout["top_level_patterns"]))

    api_surface = detect_api_artifacts(ctx.root, ctx.files)
    spec["api_surface"].update(api_surface)
    register_confidence(
        spec,
        "api_surface",
        0.2
        + 0.6
        * bool(
            api_surface["openapi_files"]
            or api_surface["graphql_files"]
            or api_surface["route_files"]
        ),
    )

    data_assets = detect_data_artifacts(ctx.root, ctx.files, ctx.directories)
    spec["data_assets"].update(data_assets)
    register_confidence(
        spec,
        "data_assets",
        0.2 + 0.6 * bool(data_assets["ddl_files"] or data_assets["migration_dirs"]),
    )

    return spec


def serialize_spec(spec: Dict[str, Any], fmt: str = "yaml") -> str:
    fmt = fmt.lower()
    if fmt == "json":
        return json.dumps(spec, indent=2, ensure_ascii=False)
    if fmt == "yaml":
        if yaml:
            return yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)
        return _fallback_yaml(spec)
    raise ValueError(f"Unsupported format: {fmt}")


def _fallback_yaml(data: Dict[str, Any]) -> str:
    """Very small YAML encoder for environments without PyYAML."""
    def _emit(obj, indent=0):
        prefix = "  " * indent
        if isinstance(obj, dict):
            lines = []
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(_emit(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {json.dumps(value, ensure_ascii=False)}")
            return "\n".join(lines)
        if isinstance(obj, list):
            lines = []
            for item in obj:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    lines.append(_emit(item, indent + 1))
                else:
                    lines.append(f"{prefix}- {json.dumps(item, ensure_ascii=False)}")
            return "\n".join(lines)
        return f"{prefix}{json.dumps(obj, ensure_ascii=False)}"

    return _emit(data)

