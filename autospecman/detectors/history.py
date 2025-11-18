"""Git history analyzers."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from ..llm import LLMAnalyzer, LLMError, create_analyzer
except ImportError:
    LLMAnalyzer = None
    LLMError = Exception
    create_analyzer = None


@dataclass
class HistoryMetrics:
    average_commits_per_week: Optional[float]
    active_contributors: Optional[int]
    recent_release_signal: Optional[str]
    branch_strategy: Optional[str]
    branch_types: List[str]  # List of branch type prefixes found (e.g., ["feature", "fix", "hotfix"])
    commit_convention: Optional[str]
    branch_naming_pattern: Optional[str]
    tag_naming_convention: Optional[str]
    recent_tags_count: Optional[int]


def analyze_git_history(
    root: Path,
    max_commits: int = 400,
    use_llm: bool = True,
    llm_provider: str = "openai",
    llm_model: str = "gpt-3.5-turbo",
    llm_api_key: Optional[str] = None,
    llm_api_base_url: Optional[str] = None,
) -> HistoryMetrics:
    """Derive useful trends from git history if available.

    Args:
        root: Repository root path
        max_commits: Maximum number of commits to analyze
        use_llm: Whether to use LLM for convention detection
        llm_provider: LLM provider name (default: "openai")
        llm_model: LLM model name (default: "gpt-3.5-turbo")
        llm_api_key: Optional API key (if None, reads from environment)
        llm_api_base_url: Optional API base URL (if None, uses default OpenAI-compatible endpoint)

    Returns:
        HistoryMetrics with detected patterns
    """
    try:
        timestamps = _read_git_timestamps(root, max_commits)
        authors = _read_git_authors(root, max_commits)
        commit_messages = _read_git_messages(root, max_commits)
        branches = _read_git_branches(root)
        tags = _read_git_tags(root)
    except FileNotFoundError:
        return HistoryMetrics(None, None, None, None, [], None, None, None, None)

    cadence = None
    if timestamps:
        cadence = _commits_per_week(timestamps)

    # 基于实际的 tags 来推断发布信号，而不是提交间隔
    release_signal = _derive_release_signal_from_tags(tags, timestamps)
    if not release_signal and timestamps:
        # 如果没有 tags，才回退到基于提交间隔的推断
        release_signal = _derive_release_signal_from_commits(timestamps)

    contributors = len(authors) if authors else None

    # 检测分支策略和分支类型（不依赖 LLM）
    branch_strategy = _detect_branch_strategy(branches)
    branch_types = _detect_branch_types(branches)

    # 统计最近一年的 tags 数量
    recent_tags_count = _count_recent_tags(tags, timestamps) if tags and timestamps else None

    # 使用 LLM 或规则检测提交消息规范、分支命名模式、tag 命名规范
    if use_llm:
        llm_result = _analyze_with_llm(
            commit_messages,
            branches,
            tags,
            llm_provider,
            llm_model,
            llm_api_key,
            llm_api_base_url,
        )
        commit_convention = llm_result.get("commit_convention")
        branch_naming_pattern = llm_result.get("branch_naming_pattern")
        tag_naming_convention = llm_result.get("tag_naming_convention")
    else:
        commit_convention = _detect_commit_convention(commit_messages)
        branch_naming_pattern = _detect_branch_naming_pattern(branches)
        tag_naming_convention = _detect_tag_naming_convention(tags)
        llm_result = None

    # 如果 LLM 失败或未使用，回退到规则检测
    if not commit_convention:
        commit_convention = _detect_commit_convention(commit_messages)
    if not branch_naming_pattern:
        branch_naming_pattern = _detect_branch_naming_pattern(branches)
    if not tag_naming_convention:
        tag_naming_convention = _detect_tag_naming_convention(tags)

    return HistoryMetrics(
        cadence,
        contributors,
        release_signal,
        branch_strategy,
        branch_types,
        commit_convention,
        branch_naming_pattern,
        tag_naming_convention,
        recent_tags_count,
    )


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


def _read_git_messages(root: Path, max_commits: int) -> List[str]:
    """Read commit messages from git log."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "log",
            f"-n{max_commits}",
            "--pretty=%s",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FileNotFoundError("Not a git repository")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _read_git_branches(root: Path) -> List[str]:
    """Read all branch names."""
    result = subprocess.run(
        ["git", "-C", str(root), "branch", "-a"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FileNotFoundError("Not a git repository")
    branches = []
    for line in result.stdout.splitlines():
        branch = line.strip().lstrip("*").strip()
        if branch and not branch.startswith("remotes/"):
            branches.append(branch)
        elif branch.startswith("remotes/origin/"):
            branches.append(branch.replace("remotes/origin/", ""))
    return list(set(branches))


def _read_git_tags(root: Path) -> List[tuple[str, int]]:
    """Read git tags with their timestamps. Returns list of (tag_name, timestamp)."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "tag",
            "-l",
            "--format=%(refname:short)|%(creatordate:unix)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FileNotFoundError("Not a git repository")
    tags = []
    for line in result.stdout.splitlines():
        if "|" in line:
            parts = line.split("|", 1)
            if len(parts) == 2:
                try:
                    tags.append((parts[0], int(parts[1])))
                except ValueError:
                    continue
    return tags


def _detect_branch_strategy(branches: List[str]) -> Optional[str]:
    """Detect common branch strategies."""
    branch_lower = {b.lower() for b in branches}
    
    has_main = "main" in branch_lower
    has_master = "master" in branch_lower
    has_develop = "develop" in branch_lower or "dev" in branch_lower
    has_release = any("release" in b.lower() for b in branches)
    has_feature = any("feature" in b.lower() or "feat" in b.lower() for b in branches)
    has_hotfix = any("hotfix" in b.lower() for b in branches)
    
    if has_develop and (has_feature or has_release or has_hotfix):
        return "git-flow"
    if has_main or has_master:
        if has_develop:
            return "github-flow-with-develop"
        if has_feature or has_hotfix:
            return "feature-branch"
        return "trunk-based"
    return None


def _detect_branch_types(branches: List[str]) -> List[str]:
    """Detect all branch type prefixes used in the repository.
    
    Returns a list of branch type prefixes found (e.g., ["feature", "fix", "hotfix", "bugfix"]).
    """
    if not branches:
        return []
    
    # Filter out main branches
    main_branches = {"main", "master", "develop", "dev", "trunk", "production", "prod", "staging", "stage"}
    feature_branches = [
        b for b in branches 
        if b.lower() not in main_branches 
        and not b.startswith("HEAD")
    ]
    
    if not feature_branches:
        return []
    
    # Common branch type prefixes
    branch_type_patterns = [
        "feature", "feat",
        "fix", "bugfix", "bug",
        "hotfix",
        "release",
        "chore",
        "docs",
        "refactor",
        "test",
        "perf",
        "style",
    ]
    
    found_types = set()
    for branch in feature_branches:
        # Extract branch name (remove remote prefix if present)
        branch_name = branch
        if "/" in branch:
            # Handle remote branches like "remotes/origin/feature/xxx" or "origin/feature/xxx"
            parts = branch.split("/")
            # Find the actual branch name (usually after "origin" or "remotes/origin")
            if "origin" in parts:
                origin_idx = parts.index("origin")
                if origin_idx + 1 < len(parts):
                    branch_name = "/".join(parts[origin_idx + 1:])
            elif len(parts) > 1:
                # Take the last part or parts after remotes
                branch_name = parts[-1] if "remotes" not in parts else "/".join(parts[parts.index("remotes") + 2:])
        
        branch_lower = branch_name.lower()
        for pattern in branch_type_patterns:
            # Check if branch starts with pattern followed by - or /
            if branch_lower.startswith(pattern + "-") or branch_lower.startswith(pattern + "/"):
                found_types.add(pattern)
                break
    
    # Also check for patterns like "fixbug", "hotfix" as whole words
    for branch in feature_branches:
        branch_name = branch
        if "/" in branch:
            parts = branch.split("/")
            if "origin" in parts:
                origin_idx = parts.index("origin")
                if origin_idx + 1 < len(parts):
                    branch_name = "/".join(parts[origin_idx + 1:])
            elif len(parts) > 1:
                branch_name = parts[-1] if "remotes" not in parts else "/".join(parts[parts.index("remotes") + 2:])
        
        branch_lower = branch_name.lower()
        for pattern in ["hotfix", "bugfix"]:
            if pattern in branch_lower and (branch_lower.startswith(pattern) or branch_lower.startswith(pattern + "-") or branch_lower.startswith(pattern + "/")):
                found_types.add(pattern)
    
    return sorted(list(found_types))


def _detect_commit_convention(messages: List[str]) -> Optional[str]:
    """Detect commit message conventions."""
    if not messages:
        return None
    
    # Conventional Commits pattern: type(scope): description
    conventional_pattern = re.compile(r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?:", re.IGNORECASE)
    conventional_count = sum(1 for msg in messages if conventional_pattern.match(msg))
    
    # Angular pattern: type(scope): description (similar but different types)
    angular_pattern = re.compile(r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert|feat!|fix!)(\(.+\))?:", re.IGNORECASE)
    angular_count = sum(1 for msg in messages if angular_pattern.match(msg))
    
    # Check if majority follow a convention
    threshold = len(messages) * 0.5
    if conventional_count >= threshold:
        return "conventional-commits"
    if angular_count >= threshold:
        return "angular-style"
    
    # Check for other patterns
    if any(msg.startswith(("Merge", "merge")) for msg in messages[:10]):
        return None  # Just merge commits, no clear convention
    
    return None


def _derive_release_signal_from_tags(tags: List[tuple[str, int]], timestamps: List[int]) -> Optional[str]:
    """Derive release signal from actual git tags."""
    if not tags or not timestamps:
        return None
    
    if len(tags) < 2:
        return "tagged" if tags else None
    
    # Sort tags by timestamp
    tags_sorted = sorted(tags, key=lambda x: x[1])
    
    # Calculate average time between tags (in days)
    if len(tags_sorted) < 2:
        return "tagged"
    
    tag_deltas = [
        (tags_sorted[i][1] - tags_sorted[i-1][1]) / (24 * 3600)
        for i in range(1, len(tags_sorted))
    ]
    
    if not tag_deltas:
        return "tagged"
    
    avg_delta = sum(tag_deltas) / len(tag_deltas)
    
    if avg_delta < 7:
        return "frequent-releases"
    if avg_delta < 30:
        return "monthly-releases"
    if avg_delta < 90:
        return "quarterly-releases"
    return "infrequent-releases"


def _derive_release_signal_from_commits(timestamps: List[int]) -> Optional[str]:
    """Fallback: derive release signal from commit cadence (less accurate)."""
    if len(timestamps) < 5:
        return None
    timestamps.sort()
    deltas = [
        (timestamps[idx] - timestamps[idx - 1]) / (24 * 3600)
        for idx in range(1, len(timestamps))
    ]
    from statistics import mean
    avg_delta = mean(deltas) if deltas else None
    if avg_delta is None:
        return None
    if avg_delta < 3:
        return "fast-iteration"
    if avg_delta < 14:
        return "weekly-activity"
    if avg_delta < 45:
        return "monthly-activity"
    return "infrequent-activity"


def _count_recent_tags(tags: List[tuple[str, int]], timestamps: List[int]) -> int:
    """Count tags created in the last year."""
    if not tags or not timestamps:
        return 0
    
    # Get the most recent commit timestamp
    if not timestamps:
        return 0
    latest_commit = max(timestamps)
    one_year_ago = latest_commit - (365 * 24 * 3600)
    
    return sum(1 for _, tag_time in tags if tag_time >= one_year_ago)


def _analyze_with_llm(
    commit_messages: List[str],
    branches: List[str],
    tags: List[tuple[str, int]],
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: Optional[str] = None,
    api_base_url: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """Analyze git conventions using LLM.

    Returns:
        Dictionary with commit_convention, branch_naming_pattern, tag_naming_convention
    """
    if create_analyzer is None:
        return {}

    analyzer = create_analyzer(
        provider=provider, model=model, api_key=api_key, api_base_url=api_base_url
    )
    if analyzer is None:
        return {}

    # Filter out main branches for branch naming pattern analysis
    main_branches = {"main", "master", "develop", "dev", "trunk", "production", "prod"}
    feature_branches = [
        b for b in branches if b.lower() not in main_branches and not b.startswith("HEAD")
    ]

    # Extract tag names only
    tag_names = [tag[0] for tag in tags]

    # Limit to recent 100 commits for analysis
    recent_commits = commit_messages[:100]

    try:
        result = analyzer.analyze_git_conventions(recent_commits, feature_branches, tag_names)
        return result
    except LLMError:
        # Silently fall back to rule-based detection
        return {}


def _detect_branch_naming_pattern(branches: List[str]) -> Optional[str]:
    """Detect branch naming pattern using rule-based heuristics.
    
    Returns a pattern string that may include multiple branch types,
    e.g., "feature/{name}, fix/{name}, hotfix/{name}"
    """
    if not branches:
        return None

    # Filter out main branches
    main_branches = {"main", "master", "develop", "dev", "trunk", "production", "prod", "staging", "stage"}
    
    # Extract actual branch names from remote branches
    # Note: _read_git_branches already removes "remotes/origin/" prefix,
    # but branches might still have "origin/" prefix or be local branches
    def extract_branch_name(branch: str) -> str:
        # Remove "origin/" prefix if present (from git branch -a output)
        if branch.startswith("origin/"):
            return branch[7:]  # Remove "origin/"
        # Handle other remote formats
        if "/" in branch:
            parts = branch.split("/")
            if "origin" in parts:
                origin_idx = parts.index("origin")
                if origin_idx + 1 < len(parts):
                    return "/".join(parts[origin_idx + 1:])
        return branch
    
    feature_branches = []
    for b in branches:
        if b.startswith("HEAD") or not b.strip():
            continue
        branch_name = extract_branch_name(b)
        # Skip if it's a main branch
        if branch_name.lower() not in main_branches:
            feature_branches.append(branch_name)

    if not feature_branches:
        return None

    # Detect patterns for each branch type
    patterns = {}
    
    # Check dash patterns (e.g., "feat-xxx", "fix-xxx") and slash patterns (e.g., "feature/xxx")
    # Priority order: check longer prefixes first to avoid conflicts (e.g., "feature" before "feat")
    prefix_order = ["feature", "bugfix", "hotfix", "release", "refactor", "feat", "fix", "bug", "chore", "docs", "test", "perf", "style"]
    
    for prefix in prefix_order:
        dash_count = sum(1 for b in feature_branches if b.lower().startswith(prefix + "-"))
        slash_count = sum(1 for b in feature_branches if b.lower().startswith(prefix + "/"))
        
        total = len(feature_branches)
        # Very low threshold: at least 1 branch or 10% of branches (more lenient)
        threshold = max(1, int(total * 0.1))
        
        # Prefer slash pattern if both exist, otherwise use dash
        if slash_count >= threshold:
            # Handle feat vs feature conflict
            if prefix == "feat":
                # Only add if feature pattern not already detected
                if "feature" not in patterns:
                    patterns["feat"] = "feat/{name}"
            elif prefix == "feature":
                # Replace feat if feature is more common
                if "feat" in patterns:
                    patterns.pop("feat")
                patterns["feature"] = "feature/{name}"
            else:
                patterns[prefix] = f"{prefix}/{{name}}"
        elif dash_count >= threshold:
            if prefix == "feat":
                if "feature" not in patterns:
                    patterns["feat"] = "feat-{name}"
            elif prefix == "feature":
                if "feat" in patterns:
                    patterns.pop("feat")
                patterns["feature"] = "feature-{name}"
            else:
                patterns[prefix] = f"{prefix}-{{name}}"
    
    # If no standard patterns found, try to detect any common separator pattern
    if not patterns and feature_branches:
        # Check if branches use a common separator (dash or slash)
        dash_separated = sum(1 for b in feature_branches if "-" in b and not b.startswith("-"))
        slash_separated = sum(1 for b in feature_branches if "/" in b and not b.startswith("/"))
        
        total = len(feature_branches)
        if dash_separated >= max(1, int(total * 0.3)):
            # Most branches use dash separator
            return "{type}-{name}"
        elif slash_separated >= max(1, int(total * 0.3)):
            # Most branches use slash separator
            return "{type}/{name}"
    
    if not patterns:
        return None
    
    # Return combined pattern, sorted for consistency
    return ", ".join(sorted(patterns.values()))


def _detect_tag_naming_convention(tags: List[tuple[str, int]]) -> Optional[str]:
    """Detect tag naming convention using rule-based heuristics."""
    if not tags:
        return None

    tag_names = [tag[0] for tag in tags]

    # Semantic Versioning: v1.0.0, 1.0.0, v1.0.0-beta.1
    semver_pattern = re.compile(r"^v?\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$")
    semver_count = sum(1 for tag in tag_names if semver_pattern.match(tag))

    # Calendar Versioning: 2024.01, 2024-01-15, YYYY.MM.DD
    calver_pattern = re.compile(r"^\d{4}[.-]\d{1,2}([.-]\d{1,2})?$")
    calver_count = sum(1 for tag in tag_names if calver_pattern.match(tag))

    # Simple versioning: v1, v2, release-1, r1.0
    simple_pattern = re.compile(r"^(v|version|release|r)\d+(\.\d+)?$", re.IGNORECASE)
    simple_count = sum(1 for tag in tag_names if simple_pattern.match(tag))

    # Date-based: 20240115, 2024-01-15
    date_pattern = re.compile(r"^\d{8}$|^\d{4}-\d{2}-\d{2}$")
    date_count = sum(1 for tag in tag_names if date_pattern.match(tag))

    # Check if majority follow a convention
    threshold = len(tag_names) * 0.5

    if semver_count >= threshold:
        return "semantic-versioning"
    if calver_count >= threshold:
        return "calendar-versioning"
    if simple_count >= threshold:
        return "simple-versioning"
    if date_count >= threshold:
        return "date-based"

    return None

