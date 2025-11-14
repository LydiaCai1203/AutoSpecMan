"""Language detection heuristics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".ipynb": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
    ".swift": "swift",
    ".m": "objective-c",
    ".mm": "objective-c++",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".vue": "vue",
    ".svelte": "svelte",
    ".scala": "scala",
    ".sh": "shell",
    ".ps1": "powershell",
    ".dart": "dart",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def detect_languages(files: Iterable[Path]) -> Counter:
    """Return counts of probable languages inferred from file extensions."""
    counter: Counter = Counter()
    for path in files:
        language = LANGUAGE_MAP.get(path.suffix.lower())
        if not language:
            continue
        counter[language] += 1
    return counter


def summarize_language_usage(counter: Counter) -> List[Dict[str, float]]:
    """Convert raw counts into percentage summaries."""
    total = sum(counter.values()) or 1
    summary: List[Dict[str, float]] = []
    for lang, count in counter.most_common():
        summary.append(
            {
                "language": lang,
                "ratio": round(count / total, 3),
                "files": count,
            }
        )
    return summary

