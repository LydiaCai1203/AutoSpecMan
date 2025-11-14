"""Utilities for inspecting local repositories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


def iter_repo_files(root: Path) -> Iterable[Path]:
    """Yield file paths under a repository root, skipping .git."""
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file():
            yield path


@dataclass
class RepoContext:
    """Lightweight snapshot of repository files and metadata."""

    root: Path
    files: List[Path]
    directories: List[Path]

    @classmethod
    def from_root(cls, root: Path) -> "RepoContext":
        root = root.resolve()
        files: List[Path] = []
        directories: List[Path] = []
        for path in root.rglob("*"):
            if ".git" in path.parts:
                continue
            if path.is_dir():
                directories.append(path)
            elif path.is_file():
                files.append(path)
        return cls(root=root, files=files, directories=directories)

