"""Command line interface for AutoSpecMan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .inference import infer_spec, serialize_spec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autospecman",
        description="Infer repository specification automatically.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Path to repository (defaults to current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("yaml", "json"),
        default="yaml",
        help="Serialization format for the generated spec.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file to write the spec to. Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=400,
        help="Number of git commits to sample for history analysis.",
    )
    return parser


def run(repo: Path, fmt: str, output: Optional[Path], max_commits: int) -> int:
    spec = infer_spec(repo)
    document = serialize_spec(spec, fmt=fmt)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document)
        print(f"Spec written to {output}")
    else:
        print(document)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args.repo, args.format, args.output, args.max_commits)
    except Exception as exc:  # pragma: no cover
        parser.error(str(exc))
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

