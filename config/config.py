# config/config.py
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class CodeIndexConfig:
    """CodeIndex 相关配置"""
    db_path: str
    root_dir: str
    languages: List[str]
    include: Optional[List[str]] = None
    exclude: Optional[List[str]] = None

@dataclass
class StructureDetectorConfig:
    """结构检测器配置"""
    root_path: str
    codeindex_db_path: Optional[str] = None
    max_depth: Optional[int] = None
    languages: List[str] = None

@dataclass
class AppConfig:
    """应用主配置"""
    project_root: str
    codeindex: CodeIndexConfig
    detector: StructureDetectorConfig