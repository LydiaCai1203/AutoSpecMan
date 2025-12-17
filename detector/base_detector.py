"""
基础检测器类
提供所有检测器共用的功能
"""

import os
from pathlib import Path
from typing import Optional, List, Any, Dict

from codeindex import CodeIndexClient

from config.config import load_detector_config
from utils.codeindex_utils import CodeIndexClientManager
from abc import ABC, abstractmethod


# ============================================================================
# 语言配置（共享常量）
# ============================================================================

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
    