"""Error handling detection using CodeIndex semantic search."""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from codeindex_sdk import CodeIndexClient, CodeIndexConfig
    HAS_CODEINDEX = True
    CODEINDEX_IMPORT_ERROR = None
except ImportError as e:
    HAS_CODEINDEX = False
    CODEINDEX_IMPORT_ERROR = str(e)

from ..llm import LLMAnalyzer, create_analyzer
from ..config import load_config


def detect_error_handling(
    repo_path: Path,
    use_llm: bool = True,
    llm_provider: str = "openai",
    llm_model: str = "gpt-3.5-turbo",
    llm_api_key: Optional[str] = None,
    llm_api_base_url: Optional[str] = None,
    codeindex_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Detect error handling patterns using CodeIndex semantic search.
    
    Args:
        repo_path: Path to repository root
        use_llm: Whether to use LLM for analysis
        llm_provider: LLM provider name
        llm_model: LLM model name
        llm_api_key: LLM API key
        llm_api_base_url: LLM API base URL
        codeindex_db_path: Optional path to CodeIndex database file
        
    Returns:
        Dictionary with error_handling information
    """
    print("\n" + "="*60)
    print("🔍 开始错误处理机制分析")
    print("="*60)
    
    result = {
        "error_handling_approach": None,
        "error_handling_details": None,
        "confidence": 0.0,
    }
    
    if not HAS_CODEINDEX:
        print("❌ CodeIndex SDK 未安装，跳过错误处理检测")
        print("   导入错误详情:")
        if CODEINDEX_IMPORT_ERROR:
            print(f"     {CODEINDEX_IMPORT_ERROR}")
        else:
            print("     无法导入 codeindex_sdk 模块")
        print("\n   安装方法:")
        print("   1. 进入 ast-demo/sdk/python 目录")
        print("   2. 运行: pip install -e .")
        print("   3. 或者: pip install -e ../ast-demo/sdk/python")
        print("   4. 确保在正确的虚拟环境中安装（当前使用的是 .venv）")
        print("="*60)
        return result
    
    print("✅ CodeIndex SDK 已安装")
    
    # Try to find codeindex database
    if codeindex_db_path:
        codeindex_db = Path(codeindex_db_path)
        # If relative path, resolve relative to repo_path
        if not codeindex_db.is_absolute():
            codeindex_db = repo_path / codeindex_db
        if not codeindex_db.exists():
            print(f"❌ 指定的 CodeIndex 数据库不存在: {codeindex_db}")
            print("="*60)
            return result
        print(f"✅ 找到 CodeIndex 数据库: {codeindex_db}")
    else:
        print("📂 正在查找 CodeIndex 数据库...")
        codeindex_db = _find_codeindex_db(repo_path)
        if not codeindex_db:
            print(f"❌ 未找到 CodeIndex 数据库")
            print(f"   已搜索位置:")
            print(f"     - {repo_path / '.codeindex' / 'project.db'}")
            print(f"     - {repo_path / '.codeindex' / 'sqlite.db'}")
            print(f"     - {repo_path / '.codeindex' / f'{repo_path.name}.db'}")
            print("   提示: 请在配置文件中设置 codeindex.db_path 或确保数据库存在于上述位置")
            print("="*60)
            return result
        print(f"✅ 自动找到 CodeIndex 数据库: {codeindex_db}")
    
    # Try to detect languages from the repository
    print("\n📝 检测编程语言...")
    languages = _detect_languages_from_repo(repo_path)
    if not languages:
        print("❌ 未能检测到编程语言")
        print("="*60)
        return result
    
    print(f"✅ 检测到编程语言: {', '.join(languages)}")
    
    # Search for error handling related code
    print("\n🔎 开始语义搜索错误处理相关代码...")
    # Load config from file to get LLM settings
    config = load_config(repo_path)
    code_snippets = _search_error_handling_code(
        repo_path, codeindex_db, languages,
        llm_api_key=llm_api_key or config.llm.api_key,
        llm_api_base_url=llm_api_base_url or config.llm.api_base_url,
        embedding_model=config.llm.embedding_model,
    )
    
    if not code_snippets:
        print("❌ 未找到错误处理相关的代码片段")
        print("   可能原因:")
        print("   1. Embedding API 未配置（请在 autospecman.toml 中设置 [llm].api_key 和 [llm].api_base_url）")
        print("   2. 代码库中确实没有错误处理相关的代码")
        print("   3. CodeIndex 数据库未包含相关代码的索引")
        print("="*60)
        return result
    
    print(f"✅ 找到 {len(code_snippets)} 个相关代码片段:")
    for i, snippet in enumerate(code_snippets[:10], 1):  # 只显示前10个
        print(f"  {i}. {snippet['symbol_name']} ({snippet['symbol_kind']})")
        print(f"     文件: {snippet['file_path']}:{snippet['line_number']}")
        print(f"     相似度: {snippet['similarity']:.2f}")
        if snippet.get('summary'):
            summary = snippet['summary'][:100]
            print(f"     摘要: {summary}...")
    if len(code_snippets) > 10:
        print(f"  ... 还有 {len(code_snippets) - 10} 个结果")
    
    # Analyze code snippets with LLM if available
    if use_llm:
        print(f"\n🤖 使用 LLM 分析错误处理模式 (模型: {llm_model})...")
        analyzer = create_analyzer(
            provider=llm_provider,
            model=llm_model,
            api_key=llm_api_key,
            api_base_url=llm_api_base_url,
        )
        if analyzer:
            print("✅ LLM 分析器创建成功")
            analysis = _analyze_error_handling_with_llm(analyzer, code_snippets)
            if analysis:
                result["error_handling_approach"] = analysis.get("approach")
                result["error_handling_details"] = analysis.get("details")
                result["confidence"] = 0.7  # High confidence when LLM analysis succeeds
                print("✅ LLM 分析完成")
                print(f"   处理方式: {result['error_handling_approach']}")
                if result['error_handling_details']:
                    details = result['error_handling_details']
                    if len(details) > 200:
                        print(f"   详细信息: {details[:200]}...")
                    else:
                        print(f"   详细信息: {details}")
                else:
                    print("   详细信息: 无")
                print("="*60)
                return result
            else:
                print("❌ LLM 分析失败，回退到基础分析")
                print("   提示: 可能是 API 服务不可用、模型名称不正确或配额已用完")
                print(f"   使用的模型: {llm_model}")
                print(f"   API 端点: {llm_api_base_url or '未设置'}")
        else:
            print("❌ 无法创建 LLM 分析器，回退到基础分析")
            print("   提示: 请检查 LLM API 配置（api_key, api_base_url）")
    else:
        print("\n⚠️  LLM 分析已禁用，使用基础分析")
    
    # Fallback: basic analysis without LLM
    print("\n📊 执行基础错误处理分析...")
    result["error_handling_approach"] = _basic_error_handling_analysis(code_snippets)
    result["confidence"] = 0.4  # Lower confidence without LLM
    print(f"✅ 基础分析完成: {result['error_handling_approach']}")
    print("="*60)
    return result


def _find_codeindex_db(repo_path: Path) -> Optional[Path]:
    """Find codeindex database in the repository."""
    # Common locations for codeindex database
    possible_paths = [
        repo_path / ".codeindex" / "project.db",
        repo_path / ".codeindex" / "sqlite.db",
        repo_path / ".codeindex" / f"{repo_path.name}.db",
    ]
    
    for db_path in possible_paths:
        if db_path.exists():
            return db_path
    
    return None


def _detect_languages_from_repo(repo_path: Path) -> List[str]:
    """Detect programming languages from repository structure."""
    languages = []
    
    # Check for common language indicators
    if (repo_path / "go.mod").exists():
        languages.append("go")
    if (repo_path / "package.json").exists():
        languages.append("ts")
        languages.append("js")
    if (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists():
        languages.append("python")
    if (repo_path / "Cargo.toml").exists():
        languages.append("rust")
    if (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
        languages.append("java")
    
    return languages if languages else ["ts", "js", "python", "go"]  # Default fallback


def _search_error_handling_code(
    repo_path: Path,
    db_path: Path,
    languages: List[str],
    llm_api_key: Optional[str] = None,
    llm_api_base_url: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search for error handling related code using CodeIndex semantic search."""
    code_snippets = []
    
    # Error handling related queries (both Chinese and English)
    queries = [
        "错误处理机制",
        "error handling",
        "异常处理",
        "exception handling",
        "错误响应格式",
        "error response format",
        "自定义异常类",
        "custom exception classes",
        "错误码定义",
        "error code definitions",
    ]
    
    print(f"   搜索查询: {len(queries)} 个关键词")
    
    try:
        # Get embedding configuration from parameters, environment or config
        embedding_config = _get_embedding_config(
            llm_api_key=llm_api_key,
            llm_api_base_url=llm_api_base_url,
            embedding_model=embedding_model,
        )
        if not embedding_config.get("apiKey") or not embedding_config.get("apiEndpoint"):
            print("   ❌ 未配置 Embedding API")
            print("      需要设置以下之一（按优先级）:")
            print("      1. CLI 参数: --llm-api-key 和 --llm-api-base-url")
            print("      2. 配置文件 autospecman.toml 中的 [llm] 部分:")
            print("         api_key = \"your-api-key\"")
            print("         api_base_url = \"https://api.example.com/v1\"")
            print("      3. 环境变量: OPENAI_API_KEY 或 LLM_API_KEY")
            return code_snippets
        
        print(f"   ✅ Embedding 配置已就绪")
        print(f"      模型: {embedding_config.get('model', 'N/A')}")
        print(f"      API 端点: {embedding_config.get('apiEndpoint', 'N/A')}")
        
        config = CodeIndexConfig(
            root_dir=str(repo_path.resolve()),
            db_path=str(db_path.resolve()),
            languages=languages,
            embedding_options=embedding_config,
        )
        
        with CodeIndexClient(config) as client:
            for i, query in enumerate(queries, 1):
                try:
                    print(f"   [{i}/{len(queries)}] 搜索: '{query}'...", end=" ", flush=True)
                    results = client.semantic_search(
                        query=query,
                        topK=5,
                        minSimilarity=0.6,
                        embeddingOptions=embedding_config,  # 传递 embeddingOptions 以初始化 EmbeddingGenerator
                    )
                    print(f"找到 {len(results)} 个结果")
                    
                    for result in results:
                        symbol = result.get("symbol", {})
                        location = result.get("location", {})
                        
                        code_snippets.append({
                            "query": query,
                            "symbol_name": symbol.get("qualifiedName", ""),
                            "symbol_kind": symbol.get("kind", ""),
                            "file_path": location.get("path", ""),
                            "line_number": location.get("startLine", 0),
                            "summary": symbol.get("chunkSummary", ""),
                            "similarity": result.get("similarity", 0.0),
                        })
                except Exception as e:
                    print(f"失败: {e}")
                    # Continue with next query if one fails
                    continue
        
        # Deduplicate by symbol name and file path
        seen = set()
        unique_snippets = []
        for snippet in code_snippets:
            key = (snippet["symbol_name"], snippet["file_path"])
            if key not in seen:
                seen.add(key)
                unique_snippets.append(snippet)
        
        print(f"   去重后剩余 {len(unique_snippets)} 个唯一结果")
        return unique_snippets[:20]  # Limit to top 20 unique results
        
    except Exception as e:
        print(f"   ❌ CodeIndex 搜索失败: {e}")
        print(f"   错误详情: {traceback.format_exc()}")
        # If codeindex fails, return empty results
        return code_snippets


def _get_embedding_config(
    llm_api_key: Optional[str] = None,
    llm_api_base_url: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Get embedding configuration from parameters, config file, or environment variables.
    
    Priority order:
    1. Function parameters (highest priority)
    2. Config file (autospecman.toml)
    3. Environment variables (lowest priority)
    
    Args:
        llm_api_key: API key from function parameter (highest priority)
        llm_api_base_url: API base URL from function parameter (highest priority)
        embedding_model: Embedding model from function parameter (highest priority)
    
    Returns:
        Dictionary with embedding configuration, or empty dict if no API key found
    """
    # Priority: parameter > config file > environment variable
    # Note: config file is loaded in the caller and passed as parameters
    api_key = (
        llm_api_key
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("LLM_API_KEY")
    )
    
    api_base_url = (
        llm_api_base_url
        or os.getenv("LLM_API_BASE_URL")
        or os.getenv("OPENAI_API_BASE_URL")
        or "https://api.openai.com/v1"
    )
    
    # Embedding model: parameter > config file > environment variable > default
    model = (
        embedding_model
        or os.getenv("EMBEDDING_MODEL")
        or "text-embedding-3-small"
    )
    
    if not api_key:
        return {}
    
    # CodeIndex expects apiEndpoint to be the full embeddings endpoint URL
    api_endpoint = api_base_url.rstrip("/") + "/embeddings"
    
    return {
        "apiEndpoint": api_endpoint,
        "apiKey": api_key,
        "model": model,
    }


def _analyze_error_handling_with_llm(
    analyzer: LLMAnalyzer,
    code_snippets: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Analyze error handling patterns using LLM."""
    # Prepare code snippets summary for LLM
    snippets_text = []
    for i, snippet in enumerate(code_snippets[:15], 1):  # Limit to 15 for prompt size
        snippets_text.append(
            f"{i}. {snippet['symbol_name']} ({snippet['symbol_kind']}) "
            f"in {snippet['file_path']}:{snippet['line_number']}\n"
            f"   Summary: {snippet.get('summary', 'N/A')[:200]}"
        )
    
    prompt = f"""分析以下代码片段，推断该框架的错误处理方式：

找到的相关代码片段：
{chr(10).join(snippets_text)}

请分析并返回 JSON 格式，包含以下字段：
{{
  "approach": "错误处理方式的简要描述，例如 '使用自定义异常类'、'使用错误码枚举'、'使用标准异常库'、'使用 Result 类型' 等",
  "details": "详细的错误处理机制说明，包括：1) 异常/错误类型定义方式 2) 错误传播机制 3) 错误响应格式 4) 错误码体系（如果有）"
}}

只返回 JSON，不要其他文字。"""
    
    print("   正在调用 LLM API...", end=" ", flush=True)
    try:
        # Build custom payload for error handling analysis
        url = f"{analyzer.api_base_url}/chat/completions"
        payload = {
            "model": analyzer.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a code analysis expert. Analyze error handling patterns and return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {analyzer.api_key}",
        }
        
        # Use the same HTTP call method as LLMAnalyzer
        if hasattr(analyzer, "_call_with_requests") and callable(analyzer._call_with_requests):
            response_data = analyzer._call_with_requests(url, payload, headers)
        else:
            response_data = analyzer._call_with_urllib(url, payload, headers)
        
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            print("失败: 响应为空")
            return None
        
        # Parse the JSON response
        result = json.loads(content)
        print("成功")
        
        # Extract approach and details
        return {
            "approach": result.get("approach"),
            "details": result.get("details"),
        }
    except (json.JSONDecodeError, KeyError, AttributeError, Exception) as e:
        print(f"失败: {e}")
        print(f"   错误详情: {traceback.format_exc()}")
        return None


def _basic_error_handling_analysis(
    code_snippets: List[Dict[str, Any]],
) -> str:
    """Basic error handling analysis without LLM."""
    if not code_snippets:
        return "未检测到明确的错误处理机制"
    
    # Count symbol kinds
    kind_counts = {}
    for snippet in code_snippets:
        kind = snippet.get("symbol_kind", "")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    
    # Infer approach from symbol kinds
    if any("exception" in snippet["symbol_name"].lower() for snippet in code_snippets):
        return "使用异常类进行错误处理"
    if any("error" in snippet["symbol_name"].lower() for snippet in code_snippets):
        return "使用错误类型进行错误处理"
    if any("result" in snippet["symbol_name"].lower() for snippet in code_snippets):
        return "使用 Result 类型进行错误处理"
    
    return f"检测到 {len(code_snippets)} 个相关代码片段，需要进一步分析"

