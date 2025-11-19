"""Command line interface for AutoSpecMan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .config import load_config, merge_config_with_args
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
    parser.add_argument(
        "--use-llm",
        action="store_true",
        default=True,
        help="Use LLM to analyze git conventions (default: True).",
    )
    parser.add_argument(
        "--no-llm",
        dest="use_llm",
        action="store_false",
        help="Disable LLM analysis and use rule-based detection only.",
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        default="openai",
        choices=("openai",),
        help="LLM provider to use (default: openai).",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLM model to use (default: from config file or gpt-3.5-turbo).",
    )
    parser.add_argument(
        "--llm-api-key",
        type=str,
        help="LLM API key (if not provided, reads from LLM_API_KEY or OPENAI_API_KEY env var).",
    )
    parser.add_argument(
        "--llm-api-base-url",
        type=str,
        help="LLM API base URL (e.g., https://api.example.com/v1). Defaults to OpenAI-compatible endpoint.",
    )
    parser.add_argument(
        "--codeindex-db-path",
        type=str,
        help="Path to CodeIndex database file. If not provided, will auto-detect in .codeindex/ directory.",
    )
    return parser


def run(
    repo: Path,
    fmt: str,
    output: Optional[Path],
    max_commits: int,
    use_llm: bool,
    llm_provider: str,
    llm_model: str,
    llm_api_key: Optional[str],
    llm_api_base_url: Optional[str],
    codeindex_db_path: Optional[str],
) -> int:
    spec = infer_spec(
        repo,
        max_commits=max_commits,
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_api_base_url=llm_api_base_url,
        codeindex_db_path=codeindex_db_path,
    )
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
        # Load configuration from files
        config = load_config(args.repo)

        # Merge with command-line arguments (args take precedence)
        merged_config = merge_config_with_args(
            config,
            {
                "max_commits": args.max_commits,
                "use_llm": args.use_llm,
                "llm_provider": args.llm_provider,
                "llm_model": args.llm_model,
                "llm_api_key": args.llm_api_key,
                "llm_api_base_url": args.llm_api_base_url,
                "codeindex_db_path": args.codeindex_db_path,
            },
        )

        return run(
            args.repo,
            args.format,
            args.output,
            merged_config.max_commits,
            merged_config.llm.use_llm,
            merged_config.llm.provider,
            merged_config.llm.model,
            merged_config.llm.api_key,
            merged_config.llm.api_base_url,
            merged_config.codeindex.db_path,
        )
    except Exception as exc:  # pragma: no cover
        parser.error(str(exc))
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

