"""LLM integration for analyzing git history patterns."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib import request
from urllib.error import HTTPError, URLError

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class LLMError(Exception):
    """Raised when LLM API calls fail."""

    pass


class LLMAnalyzer:
    """Analyzer using LLM to detect git conventions via HTTP API."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        """Initialize LLM analyzer.

        Args:
            provider: LLM provider name (for reference, not used for API calls)
            model: Model name to use
            api_key: API key (if None, will try to read from environment)
            api_base_url: Base URL for the API endpoint (default: OpenAI compatible)
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        
        # Default to OpenAI-compatible endpoint if not specified
        if api_base_url:
            self.api_base_url = api_base_url.rstrip("/")
        else:
            self.api_base_url = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")

        if not self.api_key:
            raise ValueError(
                "API key not provided. Set LLM_API_KEY or OPENAI_API_KEY environment variable, "
                "or provide api_key parameter."
            )

    def analyze_git_conventions(
        self,
        commit_messages: list[str],
        branch_names: list[str],
        tag_names: list[str],
    ) -> Dict[str, Optional[str]]:
        """Analyze git conventions using LLM.

        Args:
            commit_messages: List of commit message subjects (max 100)
            branch_names: List of branch names (filtered, max 50)
            tag_names: List of tag names (max 50)

        Returns:
            Dictionary with keys: commit_convention, branch_naming_pattern, tag_naming_convention
        """
        # Limit input sizes
        commit_samples = commit_messages[:100]
        branch_samples = branch_names[:50]
        tag_samples = tag_names[:50]

        prompt = self._build_prompt(commit_samples, branch_samples, tag_samples)

        try:
            response_data = self._call_api(prompt)
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content")
            
            if not content:
                raise LLMError("Empty response from LLM")

            result = json.loads(content)

            # Validate and extract results
            return {
                "commit_convention": result.get("commit_convention"),
                "branch_naming_pattern": result.get("branch_naming_pattern"),
                "tag_naming_convention": result.get("tag_naming_convention"),
            }
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            raise LLMError(f"LLM API call failed: {e}")

    def _call_api(self, prompt: str) -> Dict[str, Any]:
        """Call the LLM API using HTTP request.
        
        Uses OpenAI-compatible format by default, which works with most providers.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            API response as dictionary
        """
        url = f"{self.api_base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a git workflow analyzer. Analyze git history patterns and return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        if HAS_REQUESTS:
            return self._call_with_requests(url, payload, headers)
        else:
            return self._call_with_urllib(url, payload, headers)

    def _call_with_requests(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Call API using requests library."""
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()

    def _call_with_urllib(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Call API using urllib (standard library fallback)."""
        req_data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=req_data, headers=headers, method="POST")
        
        try:
            with request.urlopen(req, timeout=60) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                return response_data
        except HTTPError as e:
            error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise LLMError(f"HTTP error {e.code}: {error_body}")
        except URLError as e:
            raise LLMError(f"URL error: {e}")

    def _build_prompt(
        self,
        commit_messages: list[str],
        branch_names: list[str],
        tag_names: list[str],
    ) -> str:
        """Build the prompt for LLM analysis."""
        commit_text = "\n".join(f"- {msg}" for msg in commit_messages) if commit_messages else "无"
        branch_text = "\n".join(f"- {name}" for name in branch_names) if branch_names else "无"
        tag_text = "\n".join(f"- {name}" for name in tag_names) if tag_names else "无"

        return f"""分析以下 git 历史数据，推断项目的开发规范：

提交消息示例（最近 {len(commit_messages)} 条）：
{commit_text}

分支名称示例（{len(branch_names)} 个）：
{branch_text}

Tag 名称示例（{len(tag_names)} 个）：
{tag_text}

请返回 JSON 格式，包含以下字段：
{{
  "commit_convention": "提交消息规范名称和格式说明，例如 'conventional-commits with scope: feat(scope): description' 或 'conventional-commits without scope: feat: description' 或 'none'（如果没有明显规范）",
  "branch_naming_pattern": "分支命名模式，例如 'feat-{{ticket-id}}' 或 'feature/{{name}}' 或 'none'（如果没有明显模式）",
  "tag_naming_convention": "tag 命名规范，例如 'semantic-versioning (v1.0.0)' 或 'date-based (2024-01-15)' 或 'none'（如果没有明显规范）"
}}

只返回 JSON，不要其他文字。"""


def create_analyzer(
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    api_key: Optional[str] = None,
    api_base_url: Optional[str] = None,
) -> Optional[LLMAnalyzer]:
    """Create an LLM analyzer if available, otherwise return None.

    Args:
        provider: LLM provider name (for reference)
        model: Model name
        api_key: API key (optional)
        api_base_url: Base URL for the API endpoint (optional)

    Returns:
        LLMAnalyzer instance or None if not available
    """
    try:
        return LLMAnalyzer(
            provider=provider,
            model=model,
            api_key=api_key,
            api_base_url=api_base_url,
        )
    except ValueError:
        return None

