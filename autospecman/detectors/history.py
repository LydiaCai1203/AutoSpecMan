"""Git history analyzers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import List, Optional


@dataclass
class HistoryMetrics:
    average_commits_per_week: Optional[float]
    active_contributors: Optional[int]
    recent_release_signal: Optional[str]


def analyze_git_history(root: Path, max_commits: int = 400) -> HistoryMetrics:
    """Derive coarse trends from git history if available."""
    try:
        timestamps = _read_git_timestamps(root, max_commits)
        authors = _read_git_authors(root, max_commits)
    except FileNotFoundError:
        return HistoryMetrics(None, None, None)

    cadence = None
    if timestamps:
        cadence = _commits_per_week(timestamps)

    release_signal = None
    if timestamps:
        release_signal = _derive_release_signal(timestamps)

    contributors = len(authors) if authors else None
    return HistoryMetrics(cadence, contributors, release_signal)


def _read_git_timestamps(root: Path, max_commits: int) -> List[int]:
    result = subprocess.run(
        ["git", "-C", str(root), "log", f"-n{max_commits}", "--pretty=%ct"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FileNotFoundError("Not a git repository")
    values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    return values


def _read_git_authors(root: Path, max_commits: int) -> List[str]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "log",
            f"-n{max_commits}",
            "--pretty=%an <%ae>",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FileNotFoundError("Not a git repository")
    authors = list({line.strip() for line in result.stdout.splitlines() if line.strip()})
    return authors


def _commits_per_week(timestamps: List[int]) -> float:
    if len(timestamps) < 2:
        return float(len(timestamps))
    timestamps.sort()
    span_seconds = max(timestamps) - min(timestamps)
    weeks = max(span_seconds / (7 * 24 * 3600), 1 / 7)
    return round(len(timestamps) / weeks, 2)


def _derive_release_signal(timestamps: List[int]) -> Optional[str]:
    if len(timestamps) < 5:
        return None
    timestamps.sort()
    deltas = [
        (timestamps[idx] - timestamps[idx - 1]) / (24 * 3600)
        for idx in range(1, len(timestamps))
    ]
    avg_delta = mean(deltas) if deltas else None
    if avg_delta is None:
        return None
    if avg_delta < 3:
        return "fast-iteration"
    if avg_delta < 14:
        return "weekly-release"
    if avg_delta < 45:
        return "monthly-release"
    return "infrequent-release"

