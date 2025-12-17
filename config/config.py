import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
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


def load_detector_config(config_path: Optional[str] = None) -> StructureDetectorConfig:
    """
    从配置文件加载 StructureDetector 配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则查找默认配置文件
        
    Returns:
        StructureDetectorConfig 实例
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    if config_path is None:
        # 查找默认配置文件
        config_dir = Path(__file__).parent
        config_path = config_dir / "detector_config.yaml"
        
        # 如果不存在，尝试查找项目根目录下的配置文件
        if not config_path.exists():
            project_root = Path(__file__).parent.parent
            config_path = project_root / "detector_config.yaml"
    
    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    try:
        with open(config_path_obj, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件格式错误: {e}")
    
    if not config_data:
        raise ValueError("配置文件为空")
    
    # 解析项目配置
    project_config = config_data.get('project', {})
    root_path = project_config.get('root_path', '')
    if not root_path:
        # 如果配置文件中没有设置，尝试使用环境变量或当前目录
        root_path = os.getenv('DETECTOR_PROJECT_PATH', '.')
    
    max_depth = project_config.get('max_depth')
    languages = project_config.get('languages', ['go', 'python', 'typescript', 'javascript', 'java', 'rust'])
    
    # 解析 CodeIndex 配置
    codeindex_config = config_data.get('codeindex', {})
    codeindex_db_path = codeindex_config.get('db_path')
    
    return StructureDetectorConfig(
        root_path=root_path,
        codeindex_db_path=codeindex_db_path,
        max_depth=max_depth,
        languages=languages
    )


def save_detector_config(config: StructureDetectorConfig, config_path: Optional[str] = None):
    """
    保存 StructureDetector 配置到文件
    
    Args:
        config: StructureDetectorConfig 实例
        config_path: 配置文件路径，如果为 None 则使用默认路径
    """
    if config_path is None:
        config_dir = Path(__file__).parent
        config_path = config_dir / "detector_config.yaml"
    
    config_data = {
        'project': {
            'root_path': config.root_path,
            'max_depth': config.max_depth,
            'languages': config.languages or ['go', 'python', 'typescript', 'javascript', 'java', 'rust']
        },
        'codeindex': {
            'db_path': config.codeindex_db_path,
            'auto_find_strategy': 'both'
        }
    }
    
    config_path_obj = Path(config_path)
    config_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path_obj, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)