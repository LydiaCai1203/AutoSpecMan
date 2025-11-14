"""Tooling detection heuristics."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


KNOWN_PACKAGE_MANIFESTS = {
    "package.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "poetry.lock": "poetry",
    "pyproject.toml": "python-pyproject",
    "Pipfile": "pipenv",
    "requirements.txt": "pip",
    "go.mod": "go-mod",
    "Cargo.toml": "cargo",
    "Gemfile": "bundler",
    "composer.json": "composer",
}

PYPROJECT_LINTER_KEYS = {
    "tool.flake8": "flake8",
    "tool.ruff": "ruff",
    "tool.pylint": "pylint",
}

PYPROJECT_FORMATTER_KEYS = {
    "tool.black": "black",
    "tool.isort": "isort",
}

PACKAGE_JSON_DEV_DEP_KEYS = {
    "eslint": "eslint",
    "prettier": "prettier",
    "@typescript-eslint/eslint-plugin": "eslint",
    "stylelint": "stylelint",
    "husky": "husky",
    "lint-staged": "lint-staged",
    "jest": "jest",
    "vitest": "vitest",
}


def detect_package_managers(root: Path) -> List[str]:
    managers: Set[str] = set()
    for manifest, label in KNOWN_PACKAGE_MANIFESTS.items():
        if (root / manifest).exists():
            managers.add(label)
    return sorted(managers)


def _read_pyproject(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text())
    except Exception:
        return {}


def _read_package_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def detect_linters(root: Path) -> List[str]:
    linters: Set[str] = set()
    pyproject = _read_pyproject(root / "pyproject.toml")
    for key, name in PYPROJECT_LINTER_KEYS.items():
        section = _nested_get(pyproject, key.split("."))
        if section:
            linters.add(name)

    package_json = _read_package_json(root / "package.json")
    deps = _collect_dep_names(package_json)
    if "eslint" in deps:
        linters.add("eslint")
    if "stylelint" in deps:
        linters.add("stylelint")
    if "tslint" in deps:
        linters.add("tslint")

    if (root / ".golangci.yml").exists():
        linters.add("golangci-lint")

    return sorted(linters)


def detect_formatters(root: Path) -> List[str]:
    formatters: Set[str] = set()
    pyproject = _read_pyproject(root / "pyproject.toml")
    for key, name in PYPROJECT_FORMATTER_KEYS.items():
        section = _nested_get(pyproject, key.split("."))
        if section:
            formatters.add(name)

    package_json = _read_package_json(root / "package.json")
    deps = _collect_dep_names(package_json)
    if "prettier" in deps:
        formatters.add("prettier")

    if (root / ".rustfmt.toml").exists():
        formatters.add("rustfmt")
    if (root / ".clang-format").exists():
        formatters.add("clang-format")

    return sorted(formatters)


def detect_test_frameworks(root: Path) -> List[str]:
    frameworks: Set[str] = set()
    package_json = _read_package_json(root / "package.json")
    deps = _collect_dep_names(package_json)
    for candidate in ("jest", "vitest", "cypress", "playwright", "mocha"):
        if candidate in deps:
            frameworks.add(candidate)

    pyproject = _read_pyproject(root / "pyproject.toml")
    pytest_cfg = _nested_get(pyproject, ["tool", "pytest"])
    if pytest_cfg is not None or (root / "pytest.ini").exists():
        frameworks.add("pytest")
    if (root / "tox.ini").exists():
        frameworks.add("tox")
    if (root / "nose.cfg").exists():
        frameworks.add("nose")
    if (root / "go.mod").exists():
        frameworks.add("go test")

    return sorted(frameworks)


def detect_ci_systems(root: Path) -> List[str]:
    systems: Set[str] = set()
    gh_dir = root / ".github" / "workflows"
    if gh_dir.exists() and any(gh_dir.iterdir()):
        systems.add("github-actions")
    if (root / ".gitlab-ci.yml").exists():
        systems.add("gitlab-ci")
    if (root / "azure-pipelines.yml").exists():
        systems.add("azure-pipelines")
    if (root / ".circleci").exists():
        systems.add("circleci")
    if (root / ".buildkite").exists():
        systems.add("buildkite")
    return sorted(systems)


def detect_security_tools(root: Path) -> List[str]:
    tools: Set[str] = set()
    if (root / "bandit.yaml").exists() or (root / ".bandit").exists():
        tools.add("bandit")
    if (root / ".semgrep.yml").exists():
        tools.add("semgrep")
    if (root / "snyk.json").exists():
        tools.add("snyk")
    if (root / "cargo-audit.toml").exists():
        tools.add("cargo-audit")
    return sorted(tools)


def _nested_get(data: Dict, keys: Iterable[str]):
    cursor = data
    for key in keys:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
        if cursor is None:
            return None
    return cursor


def _collect_dep_names(package_json: Dict) -> Set[str]:
    deps: Set[str] = set()
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        entries = package_json.get(section, {})
        if isinstance(entries, dict):
            deps.update(entries.keys())
    return deps

