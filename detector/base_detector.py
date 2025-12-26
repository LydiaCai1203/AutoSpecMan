"""
基础检测器类
提供所有检测器共用的功能
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict
from abc import ABC, abstractmethod

from codeindex import CodeIndexClient

from config.config import load_detector_config
from utils.codeindex_utils import CodeIndexClientManager

LANGUAGE_EXTENSIONS = {
    'python': ['.py'],
    'go': ['.go'],
    'typescript': ['.ts', '.tsx'],
    'javascript': ['.js', '.jsx'],
    'java': ['.java'],
    'rust': ['.rs'],
    'html': ['.html', '.htm'],
}

EXCLUDE_PATTERNS = [
    '.git', '.svn', '.hg',
    'node_modules', '__pycache__', '.pytest_cache',
    'vendor', 'dist', 'build', 'target',
    '.codeindex', '.idea', '.vscode',
]

# CodeIndex 语言代码映射
CODEINDEX_LANGUAGE_MAP = {
    'go': 'go',
    'python': 'python',
    'typescript': 'ts',
    'javascript': 'js',
    'java': 'java',
    'rust': 'rust',
    'html': 'html',
}

class BaseDetector(ABC):
    """基础检测器类"""
    
    def __init__(self, config_path: str, config_type: str):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
            config_type: 配置类型
        """
        # TODO: 是否可以根据子类自动识别
        self.config = load_detector_config(config_path, config_type)

    def _get_file_language(self, file_path: str) -> Optional[str]:
        """
        根据文件扩展名识别语言
        
        Args:
            file_path: 文件路径
            
        Returns:
            语言名称，如果无法识别返回 None
        """
        ext = Path(file_path).suffix.lower()
        for lang, extensions in LANGUAGE_EXTENSIONS.items():
            if ext in extensions:
                return lang
        return None
    
    def _should_exclude(self, path: str) -> bool:
        """
        判断路径是否应该被排除
        
        Args:
            path: 路径字符串
            
        Returns:
            如果应该排除返回 True
        """
        path_parts = Path(path).parts
        for part in path_parts:
            if any(pattern in part.lower() for pattern in EXCLUDE_PATTERNS):
                return True
        return False
    
    def _scan_files(self) -> List[str]:
        """
        扫描项目文件（返回文件路径列表）
        
        Returns:
            文件路径列表
        """
        files = []
        
        for root, dirs, filenames in os.walk(self.config.root_path):
            root_path = Path(root)
            
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if not self._should_exclude(str(root_path / d))]
            for filename in filenames:
                file_path = root_path / filename
                
                if self._should_exclude(str(file_path)):
                    continue
                
                language = self._get_file_language(str(file_path))
                if language and language in self.config.languages:
                    files.append(str(file_path))
        
        return files

    @abstractmethod
    def detect(self) -> Any:
        """
        执行检测流程（子类必须实现）
        
        Returns:
            检测结果（类型由子类决定）
        """
        pass
    
    @abstractmethod
    def detect_to_file(self, output_path: str):
        """
        检测并输出到文件（子类必须实现）
        
        Args:
            output_path: 输出文件路径
        """
        pass


class CodeIndexQuery:
    """CodeIndex 查询类"""

    def __init__(self, codeindex_db_path: str):
        self.codeindex_db_path = codeindex_db_path
        self.codeindex_manager = CodeIndexClientManager.get_instance()

    @property
    def codeindex_cli(self) -> CodeIndexClient:
        return self.codeindex_manager.get_client(self.codeindex_db_path)

    def _query_symbols_batch(self, symbol_names: List[str], language: str) -> List[Dict[str, Any]]:
        """
        批量查询符号
        
        Args:
            symbol_names: 符号名列表
            language: 语言类型
            
        Returns:
            符号记录列表
        """
        if not self.codeindex_cli:
            return []
        
        codeindex_lang = CODEINDEX_LANGUAGE_MAP.get(language)
        if not codeindex_lang:
            return []
        
        all_symbols: List[Dict[str, Any]] = []
        for symbol_name in symbol_names:
            try:
                symbols = self.codeindex_cli.find_symbols(
                    name=symbol_name,
                    language=codeindex_lang
                )
                all_symbols.extend(symbols)
            except Exception:
                continue
        
        return all_symbols
    
    def _get_symbol_summaries(self, symbols: List[Dict[str, Any]]) -> List[str]:
        """
        从符号记录中提取摘要
        
        Args:
            symbols: 符号记录列表
            
        Returns:
            摘要列表（过滤空值）
        """
        summaries = []
        for symbol in symbols:
            summary = symbol.get('chunkSummary')
            if summary and summary.strip():
                summaries.append(summary.strip())
        return summaries
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        language: Optional[str] = None,
        kind: Optional[str] = None,
        min_similarity: float = 0.7,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        自然语言语义搜索
        
        使用自然语言查询代码，自动生成 embedding 并搜索相似的符号。
        需要先使用 CodeIndex CLI 生成 embedding：
            node dist/cli/index.js embed --db <db_path>
        
        Args:
            query: 自然语言查询文本，例如："用户登录验证"
            top_k: 返回结果数量，默认 10
            language: 语言过滤器，例如："go", "python", "typescript"
            kind: 符号类型过滤器，例如："function", "class", "struct"
            min_similarity: 最小相似度阈值（0.0-1.0），默认 0.7
            **kwargs: 其他参数，如 api_endpoint, api_key, model 等
        
        Returns:
            搜索结果列表，每个结果包含：
            - symbol: 符号信息（name, kind, qualifiedName, chunkSummary 等）
            - similarity: 相似度分数（0.0-1.0）
            - location: 位置信息（path, startLine, endLine 等）
        
        Examples:
            # 基本用法
            results = codeindex_query.semantic_search("用户登录验证", top_k=5)
            
            # 带过滤条件
            results = codeindex_query.semantic_search(
                query="用户登录验证",
                top_k=5,
                language="go",
                kind="function",
                min_similarity=0.7
            )
        """
        if not self.codeindex_cli:
            return []
        
        codeindex_lang = None
        if language:
            codeindex_lang = CODEINDEX_LANGUAGE_MAP.get(language.lower())
            if not codeindex_lang:
                codeindex_lang = language.lower()
        
        try:
            embedding_config = self._load_embedding_config()
            if embedding_config:
                if 'api_endpoint' not in kwargs:
                    kwargs['api_endpoint'] = embedding_config.get('apiEndpoint')
                if 'api_key' not in kwargs:
                    kwargs['api_key'] = embedding_config.get('apiKey')
                if 'model' not in kwargs:
                    kwargs['model'] = embedding_config.get('model') or embedding_config.get('defaultModel')
                if 'dimension' not in kwargs:
                    kwargs['dimension'] = embedding_config.get('dimension')
            
            if not kwargs.get('api_endpoint') and not kwargs.get('api_key'):
                logging.warning("未找到 embedding 配置，语义搜索可能失败")
            
            results = self.codeindex_cli.semantic_search(
                query=query,
                top_k=top_k,
                language=codeindex_lang,
                kind=kind,
                min_similarity=min_similarity,
                **kwargs
            )
            return results
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logging.warning(f"语义搜索失败: {e}\n{error_detail}")
            return []
    
    def _load_embedding_config(self) -> Optional[Dict[str, Any]]:
        """
        从配置文件加载 embedding 配置
        
        Returns:
            embedding 配置字典，如果未找到返回 None
        """
        # 尝试从数据库路径的目录及其父目录查找配置文件
        db_path = Path(self.codeindex_db_path).resolve()
        search_dirs = [
            db_path.parent,  # 数据库目录
            Path.cwd(),  # 当前工作目录
        ]
        
        # 添加父目录（最多5层）
        current = db_path.parent
        for _ in range(5):
            search_dirs.append(current)
            if current == current.parent:  # 到达根目录
                break
            current = current.parent
        
        # 搜索配置文件
        for search_dir in search_dirs:
            config_path = search_dir / 'codeindex.config.json'
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        embedding_config = config_data.get('embedding')
                        if embedding_config:
                            logging.debug(f"从 {config_path} 加载 embedding 配置成功")
                            return embedding_config
                except Exception as e:
                    logging.debug(f"读取配置文件 {config_path} 失败: {e}")
                    continue
        
        logging.warning(f"未找到 codeindex.config.json 配置文件。搜索路径: {[str(d) for d in search_dirs]}")
        return None
    
    def get_semantic_search_summaries(
        self,
        query: str,
        top_k: int = 10,
        language: Optional[str] = None,
        kind: Optional[str] = None,
        min_similarity: float = 0.7,
        **kwargs
    ) -> List[str]:
        """
        执行语义搜索并提取摘要
        
        这是 semantic_search 的便捷方法，直接返回摘要列表。
        
        Args:
            query: 自然语言查询文本
            top_k: 返回结果数量，默认 10
            language: 语言过滤器
            kind: 符号类型过滤器
            min_similarity: 最小相似度阈值，默认 0.7
            **kwargs: 其他参数
        
        Returns:
            摘要列表（过滤空值）
        """
        results = self.semantic_search(
            query=query,
            top_k=top_k,
            language=language,
            kind=kind,
            min_similarity=min_similarity,
            **kwargs
        )
        
        summaries = []
        for result in results:
            symbol = result.get('symbol', {})
            summary = symbol.get('chunkSummary')
            if summary and summary.strip():
                summaries.append(summary.strip())
        
        return summaries
    
    def get_semantic_search_symbols(
        self,
        query: str,
        top_k: int = 10,
        language: Optional[str] = None,
        kind: Optional[str] = None,
        min_similarity: float = 0.7,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        执行语义搜索并返回符号信息
        
        这是 semantic_search 的便捷方法，返回符号信息列表（不包含 similarity 和 location）。
        
        Args:
            query: 自然语言查询文本
            top_k: 返回结果数量，默认 10
            language: 语言过滤器
            kind: 符号类型过滤器
            min_similarity: 最小相似度阈值，默认 0.7
            **kwargs: 其他参数
        
        Returns:
            符号信息列表
        """
        results = self.semantic_search(
            query=query,
            top_k=top_k,
            language=language,
            kind=kind,
            min_similarity=min_similarity,
            **kwargs
        )
        
        symbols = []
        for result in results:
            symbol = result.get('symbol', {})
            if symbol:
                symbols.append(symbol)
        
        return symbols
    