"""Format spec for AI consumption: natural language + structured rules + examples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def format_for_ai(spec: Dict[str, Any], repo_path: Path) -> str:
    """Format spec as AI-friendly document with three sections:
    
    1. Natural language instructions (why to follow)
    2. Structured JSON rules (what to follow)
    3. Examples (how to follow)
    
    Args:
        spec: The inferred spec dictionary
        repo_path: Path to repository root
        
    Returns:
        Formatted markdown document
    """
    # Section I: Natural language instructions
    instructions = _build_instructions()
    
    # Section II: Convert facts to rules (structured JSON)
    rules = _facts_to_rules(spec, repo_path)
    
    # Section III: Examples
    examples = _build_examples(spec, repo_path)
    
    # Combine all sections
    return f"""{instructions}

---

## Structured Rules (JSON)

```json
{json.dumps(rules, indent=2, ensure_ascii=False)}
```

---

## Examples

{examples}
"""


def _build_instructions() -> str:
    """Build natural language instructions for AI."""
    return """# Project Specification

This project has an established coding and architectural style. 

**You MUST follow the project's inferred conventions in directory structure, naming, error handling, and file layout.**

All rules below override your defaults.

**Do NOT introduce new frameworks, directories, naming patterns, or error structures unless explicitly allowed.**

When generating code:
- Follow the directory conventions strictly
- Use the naming patterns exactly as specified
- Implement error handling using the established approach
- Match the code style and structure patterns
- Respect the testing conventions
- Do not deviate from these rules for "better" alternatives

These rules are derived from the actual codebase and represent the project's established patterns."""


def _facts_to_rules(spec: Dict[str, Any], repo_path: Path) -> Dict[str, Any]:
    """Convert detected facts into actionable rules for AI."""
    rules: Dict[str, Any] = {
        "project_signature": {},
        "directory_conventions": {},
        "naming_conventions": {},
        "error_handling": {},
        "code_style": {},
        "testing_conventions": {},
        "generation_rules": {},
    }
    
    # Project signature
    lang_stack = spec.get("language_stack", [])
    if lang_stack:
        primary_lang = lang_stack[0].get("language", "unknown")
        rules["project_signature"]["language"] = primary_lang
        rules["project_signature"]["project_type"] = _infer_project_type(spec)
    
    # Directory conventions
    structure = spec.get("structure", {})
    top_level = structure.get("top_level_patterns", [])
    service_markers = structure.get("service_markers", [])
    notable_dirs = structure.get("notable_directories", [])
    
    # Extract actual directory names (filter out .venv, node_modules, etc.)
    actual_dirs = [
        d for d in notable_dirs 
        if not any(skip in d for skip in [".venv", "node_modules", "site-packages", ".git"])
    ]
    
    if actual_dirs:
        # Get unique top-level directories
        root_dirs = list(set(Path(d).parts[0] for d in actual_dirs if Path(d).parts))
        rules["directory_conventions"]["root_dirs"] = sorted(root_dirs)
    
    if service_markers:
        rules["directory_conventions"]["module_structure_rules"] = [
            f"modules may contain: {', '.join(service_markers)}"
        ]
    
    rules["directory_conventions"]["file_creation_rules"] = [
        "new modules should follow existing directory structure",
        "do not create new top-level folders without explicit permission"
    ]
    
    # Naming conventions (infer from language)
    primary_lang = rules["project_signature"].get("language", "python")
    rules["naming_conventions"] = _get_naming_conventions(primary_lang)
    
    # Error handling
    error_info = spec.get("error_handling", {})
    if error_info.get("error_handling_approach"):
        rules["error_handling"]["style"] = error_info["error_handling_approach"]
        rules["error_handling"]["rules"] = [
            f"use {error_info['error_handling_approach']}",
            "follow the established error handling pattern"
        ]
        if error_info.get("error_handling_details"):
            rules["error_handling"]["notes"] = error_info["error_handling_details"]
    
    # Code style
    tooling = spec.get("tooling", {})
    formatters = tooling.get("formatters", [])
    linters = tooling.get("linters", [])
    
    rules["code_style"] = {
        "imports": "absolute preferred, relative allowed in packages",
        "docstring": _infer_docstring_style(primary_lang),
        "public_api_rules": [
            "no wildcard imports",
            "export objects via __all__ when public"
        ]
    }
    
    if formatters:
        rules["code_style"]["formatters"] = formatters
    if linters:
        rules["code_style"]["linters"] = linters
    
    # Testing conventions
    test_frameworks = tooling.get("test_frameworks", [])
    if test_frameworks:
        rules["testing_conventions"]["framework"] = test_frameworks[0]
        rules["testing_conventions"]["layout"] = _infer_test_layout(primary_lang, test_frameworks[0])
        rules["testing_conventions"]["naming_rules"] = _infer_test_naming(primary_lang, test_frameworks[0])
    
    # Generation rules
    rules["generation_rules"] = {
        "when_creating_new_code": [
            "follow directory_conventions.root_dirs",
            "follow naming_conventions",
            "follow error_handling rules",
            "never introduce new architectural patterns",
            "match existing code style"
        ]
    }
    
    # Workflow conventions
    workflow = spec.get("workflow", {})
    if workflow.get("commit_convention"):
        rules["workflow"] = {
            "commit_convention": workflow["commit_convention"],
            "branch_naming_pattern": workflow.get("branch_naming_pattern"),
            "tag_naming_convention": workflow.get("tag_naming_convention"),
        }
    
    return rules


def _infer_project_type(spec: Dict[str, Any]) -> str:
    """Infer project type from structure and tooling."""
    structure = spec.get("structure", {})
    tooling = spec.get("tooling", {})
    
    # Check for CLI indicators
    if any("cli" in str(d).lower() for d in structure.get("notable_directories", [])):
        return "cli"
    
    # Check for service indicators
    if any(marker in ["routes", "controllers", "api"] for marker in structure.get("service_markers", [])):
        return "service"
    
    # Check for library indicators
    if tooling.get("package_managers"):
        return "library"
    
    return "unknown"


def _get_naming_conventions(language: str) -> Dict[str, str]:
    """Get naming conventions for a language."""
    conventions = {
        "python": {
            "files": "snake_case.py",
            "modules": "snake_case",
            "classes": "PascalCase",
            "functions": "snake_case",
            "constants": "UPPER_CASE",
            "private": "_leading_underscore",
        },
        "typescript": {
            "files": "kebab-case.ts or PascalCase.tsx",
            "modules": "camelCase",
            "classes": "PascalCase",
            "functions": "camelCase",
            "constants": "UPPER_CASE or camelCase",
        },
        "javascript": {
            "files": "kebab-case.js or camelCase.js",
            "modules": "camelCase",
            "classes": "PascalCase",
            "functions": "camelCase",
            "constants": "UPPER_CASE",
        },
        "go": {
            "files": "snake_case.go",
            "packages": "lowercase",
            "types": "PascalCase",
            "functions": "PascalCase (exported) or camelCase (private)",
            "constants": "PascalCase or UPPER_CASE",
        },
        "java": {
            "files": "PascalCase.java",
            "packages": "lowercase",
            "classes": "PascalCase",
            "methods": "camelCase",
            "constants": "UPPER_CASE",
        },
    }
    return conventions.get(language.lower(), {
        "files": "snake_case",
        "modules": "snake_case",
        "classes": "PascalCase",
        "functions": "camelCase",
    })


def _infer_docstring_style(language: str) -> str:
    """Infer docstring style from language."""
    if language.lower() == "python":
        return "google_style"  # Most common
    return "none"


def _infer_test_layout(language: str, framework: str) -> str:
    """Infer test layout from language and framework."""
    if language.lower() == "python" and framework.lower() == "pytest":
        return "tests/<module>/test_xxx.py or tests/test_xxx.py"
    if language.lower() == "python" and framework.lower() == "unittest":
        return "tests/<module>/test_xxx.py"
    if language.lower() in ["typescript", "javascript"]:
        return "tests/<module>/xxx.test.ts or __tests__/xxx.test.ts"
    return "tests/<module>/test_xxx"


def _infer_test_naming(language: str, framework: str) -> str:
    """Infer test naming rules."""
    if framework.lower() == "pytest":
        return "test_<function_name>"
    if framework.lower() == "unittest":
        return "test_<method_name>"
    if framework.lower() in ["jest", "vitest"]:
        return "test('<description>') or describe('<group>')"
    return "test_<name>"


def _build_examples(spec: Dict[str, Any], repo_path: Path) -> str:
    """Build example section from spec."""
    examples = []
    
    # Get primary language first
    lang_stack = spec.get("language_stack", [])
    primary_lang = lang_stack[0].get("language", "python") if lang_stack else "python"
    
    # Directory structure example
    structure = spec.get("structure", {})
    notable_dirs = structure.get("notable_directories", [])
    if notable_dirs:
        # Get clean directory examples
        clean_dirs = [
            d for d in notable_dirs 
            if not any(skip in d for skip in [".venv", "node_modules", "site-packages", ".git"])
        ][:5]  # Limit to 5 examples
        
        if clean_dirs:
            examples.append("### Directory Structure Example\n")
            examples.append("When creating new files, follow this structure:\n")
            for dir_path in clean_dirs[:3]:
                try:
                    if Path(dir_path).is_absolute():
                        rel_path = Path(dir_path).relative_to(repo_path)
                    else:
                        rel_path = Path(dir_path)
                    examples.append(f"- `{rel_path}`")
                except ValueError:
                    # Path not relative to repo, use as-is
                    examples.append(f"- `{dir_path}`")
            examples.append("")
    
    # Naming example
    if lang_stack:
        naming = _get_naming_conventions(primary_lang)
        
        examples.append("### Naming Convention Examples\n")
        examples.append(f"**Files:** `{naming.get('files', 'snake_case')}`")
        examples.append(f"**Classes:** `{naming.get('classes', 'PascalCase')}`")
        examples.append(f"**Functions:** `{naming.get('functions', 'snake_case')}`")
        examples.append("")
    
    # Error handling example
    error_info = spec.get("error_handling", {})
    if error_info.get("error_handling_approach"):
        examples.append("### Error Handling Example\n")
        examples.append(f"**Style:** {error_info['error_handling_approach']}")
        if error_info.get("error_handling_details"):
            details = error_info["error_handling_details"]
            if len(details) > 200:
                details = details[:200] + "..."
            examples.append(f"**Details:** {details}")
        examples.append("")
    
    # Testing example
    tooling = spec.get("tooling", {})
    test_frameworks = tooling.get("test_frameworks", [])
    if test_frameworks:
        framework = test_frameworks[0]
        examples.append("### Testing Example\n")
        examples.append(f"**Framework:** {framework}")
        test_layout = _infer_test_layout(primary_lang, framework)
        test_naming = _infer_test_naming(primary_lang, framework)
        examples.append(f"**Layout:** {test_layout}")
        examples.append(f"**Naming:** {test_naming}")
        examples.append("")
    
    if not examples:
        return "Examples will be generated based on detected patterns."
    
    return "\n".join(examples)

