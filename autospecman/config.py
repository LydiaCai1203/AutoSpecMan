"""Configuration management for AutoSpecMan."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None


@dataclass
class LLMConfig:
    """LLM configuration settings."""

    use_llm: bool = True
    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    embedding_model: Optional[str] = None  # Embedding model for CodeIndex semantic search


@dataclass
class CodeIndexConfig:
    """CodeIndex configuration settings."""

    db_path: Optional[str] = None  # Path to codeindex database, if None will auto-detect

    def __post_init__(self):
        pass


@dataclass
class Config:
    """AutoSpecMan configuration."""

    max_commits: int = 400
    llm: LLMConfig = None
    codeindex: CodeIndexConfig = None

    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()
        if self.codeindex is None:
            self.codeindex = CodeIndexConfig()


def find_config_files(repo_path: Path) -> list[Path]:
    """Find configuration files in order of precedence.

    Returns:
        List of config file paths, ordered from highest to lowest precedence
    """
    config_files = []

    # 1. Project-level config (in repository root)
    repo_root = repo_path.resolve()
    for name in ("autospecman.toml", ".autospecman.toml"):
        config_path = repo_root / name
        if config_path.exists():
            config_files.append(config_path)

    # 2. User-level config
    home = Path.home()
    for base in (home / ".autospecman", home / ".config" / "autospecman"):
        config_path = base / "config.toml"
        if config_path.exists():
            config_files.append(config_path)

    return config_files


def load_config(repo_path: Path) -> Config:
    """Load configuration from files and environment.

    Configuration precedence (highest to lowest):
    1. Environment variables
    2. Project-level config file (autospecman.toml or .autospecman.toml)
    3. User-level config file (~/.autospecman/config.toml or ~/.config/autospecman/config.toml)
    4. Default values

    Args:
        repo_path: Path to repository root

    Returns:
        Config object with loaded settings
    """
    config = Config()

    if tomllib is None:
        # If tomllib is not available, only use environment variables
        _load_from_env(config)
        return config

    # Load from config files (lowest to highest precedence, so later files override earlier ones)
    config_files = find_config_files(repo_path)
    for config_file in config_files:
        try:
            with open(config_file, "rb") as f:
                data = tomllib.load(f)
                _load_from_dict(config, data)
        except Exception:
            # Silently ignore config file errors
            continue

    # Environment variables override config files
    _load_from_env(config)

    return config


def _load_from_dict(config: Config, data: dict) -> None:
    """Load configuration from a dictionary."""
    if "max_commits" in data:
        config.max_commits = int(data["max_commits"])

    if "llm" in data:
        llm_data = data["llm"]
        if isinstance(llm_data, dict):
            if "use_llm" in llm_data:
                config.llm.use_llm = bool(llm_data["use_llm"])
            if "provider" in llm_data:
                config.llm.provider = str(llm_data["provider"])
            if "model" in llm_data:
                config.llm.model = str(llm_data["model"])
            if "api_key" in llm_data:
                config.llm.api_key = str(llm_data["api_key"])
            if "api_base_url" in llm_data:
                config.llm.api_base_url = str(llm_data["api_base_url"])
            if "embedding_model" in llm_data:
                config.llm.embedding_model = str(llm_data["embedding_model"])

    if "codeindex" in data:
        codeindex_data = data["codeindex"]
        if isinstance(codeindex_data, dict):
            if "db_path" in codeindex_data:
                config.codeindex.db_path = str(codeindex_data["db_path"])


def _load_from_env(config: Config) -> None:
    """Load configuration from environment variables."""
    # max_commits
    if "AUTOSPECMAN_MAX_COMMITS" in os.environ:
        try:
            config.max_commits = int(os.environ["AUTOSPECMAN_MAX_COMMITS"])
        except ValueError:
            pass

    # LLM settings
    if "AUTOSPECMAN_USE_LLM" in os.environ:
        config.llm.use_llm = os.environ["AUTOSPECMAN_USE_LLM"].lower() in ("1", "true", "yes")

    if "AUTOSPECMAN_LLM_PROVIDER" in os.environ:
        config.llm.provider = os.environ["AUTOSPECMAN_LLM_PROVIDER"]

    if "AUTOSPECMAN_LLM_MODEL" in os.environ:
        config.llm.model = os.environ["AUTOSPECMAN_LLM_MODEL"]

    # API key from environment (LLM_API_KEY takes precedence, then OPENAI_API_KEY for compatibility)
    if "LLM_API_KEY" in os.environ:
        config.llm.api_key = os.environ["LLM_API_KEY"]
    elif "OPENAI_API_KEY" in os.environ:
        config.llm.api_key = os.environ["OPENAI_API_KEY"]
    elif "AUTOSPECMAN_LLM_API_KEY" in os.environ:
        config.llm.api_key = os.environ["AUTOSPECMAN_LLM_API_KEY"]

    # API base URL
    if "LLM_API_BASE_URL" in os.environ:
        config.llm.api_base_url = os.environ["LLM_API_BASE_URL"]
    elif "AUTOSPECMAN_LLM_API_BASE_URL" in os.environ:
        config.llm.api_base_url = os.environ["AUTOSPECMAN_LLM_API_BASE_URL"]

    # CodeIndex settings
    if "AUTOSPECMAN_CODEINDEX_DB_PATH" in os.environ:
        config.codeindex.db_path = os.environ["AUTOSPECMAN_CODEINDEX_DB_PATH"]


def merge_config_with_args(config: Config, args: dict) -> Config:
    """Merge command-line arguments with config, with args taking precedence.

    Args:
        config: Base configuration
        args: Command-line arguments (from argparse)

    Returns:
        Merged configuration
    """
    merged = Config()
    merged.max_commits = args.get("max_commits", config.max_commits)
    merged.llm = LLMConfig()
    merged.codeindex = CodeIndexConfig()

    # LLM settings
    merged.llm.use_llm = args.get("use_llm", config.llm.use_llm)
    merged.llm.provider = args.get("llm_provider", config.llm.provider)
    # Model: CLI arg (if provided) > config file > default
    merged.llm.model = args.get("llm_model") or config.llm.model or "gpt-3.5-turbo"
    # API key: CLI arg > config file > env var
    merged.llm.api_key = (
        args.get("llm_api_key")
        or config.llm.api_key
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    # API base URL: CLI arg > config file > env var
    merged.llm.api_base_url = (
        args.get("llm_api_base_url")
        or config.llm.api_base_url
        or os.getenv("LLM_API_BASE_URL")
        or None  # Will use default OpenAI-compatible endpoint
    )

    # CodeIndex settings
    merged.codeindex.db_path = (
        args.get("codeindex_db_path")
        or config.codeindex.db_path
        or os.getenv("AUTOSPECMAN_CODEINDEX_DB_PATH")
        or None
    )

    return merged

