import yaml
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union

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
class CodeStyleDetectorConfig:
    """代码风格检测器配置"""
    root_path: str
    codeindex_db_path: Optional[str] = None
    languages: Optional[List[str]] = None

@dataclass
class GitDetectorConfig:
    """Git 检测器配置"""
    root_path: str
    analyze_commits_count: int = 100  # 分析的提交数量（用于识别习惯）
    git_repo_path: Optional[str] = None  # 如果与 root_path 不同

@dataclass
class ApiDesignDetectorConfig:
    """API 设计规范检测器配置"""
    root_path: str
    codeindex_db_path: Optional[str] = None
    languages: Optional[List[str]] = None
    analyze_frameworks: Optional[List[str]] = None  # 可选：指定要分析的框架

@dataclass
class AppConfig:
    """应用主配置"""
    project_root: str
    codeindex: CodeIndexConfig
    detector: StructureDetectorConfig


def _load_config_data(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    从配置文件加载原始配置数据（公共函数）
    
    Args:
        config_path: 配置文件路径，如果为 None 则查找默认配置文件
        
    Returns:
        配置数据字典
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件格式错误: {e}")
    
    if not config_data:
        raise ValueError("配置文件为空")
    
    return config_data


def _parse_common_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析通用配置项（root_path, languages）
    
    Args:
        config_data: 配置数据字典
        
    Returns:
        包含通用配置项的字典
    """
    project_config = config_data.get('project', {})
    root_path = project_config.get('root_path', '')
    languages = project_config.get('languages', ['go', 'python', 'typescript', 'javascript', 'java', 'rust'])
    return {
        'root_path': root_path,
        'languages': languages
    }


def load_structure_detector_config(config_path: Optional[str] = None) -> StructureDetectorConfig:
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
    config_data = _load_config_data(config_path)
    common_config = _parse_common_config(config_data)
    
    project_config = config_data.get('project', {})
    max_depth = project_config.get('max_depth')
    
    codeindex_config = config_data.get('codeindex', {})
    codeindex_db_path = codeindex_config.get('db_path')
    
    return StructureDetectorConfig(
        root_path=common_config['root_path'],
        codeindex_db_path=codeindex_db_path,
        max_depth=max_depth,
        languages=common_config['languages']
    )


def load_codestyle_detector_config(config_path: Optional[str] = None) -> CodeStyleDetectorConfig:
    """
    从配置文件加载 CodeStyleDetector 配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则查找默认配置文件
        
    Returns:
        CodeStyleDetectorConfig 实例
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    config_data = _load_config_data(config_path)
    common_config = _parse_common_config(config_data)
    
    codeindex_config = config_data.get('codeindex', {})
    codeindex_db_path = codeindex_config.get('db_path')
    
    return CodeStyleDetectorConfig(
        root_path=common_config['root_path'],
        codeindex_db_path=codeindex_db_path,
        languages=common_config['languages']
    )


def load_git_detector_config(config_path: Optional[str] = None) -> GitDetectorConfig:
    """
    从配置文件加载 GitDetector 配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则查找默认配置文件
        
    Returns:
        GitDetectorConfig 实例
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    config_data = _load_config_data(config_path)
    common_config = _parse_common_config(config_data)
    
    git_config = config_data.get('git', {})
    analyze_commits_count = git_config.get('analyze_commits_count', 100)
    git_repo_path = git_config.get('repo_path')
    
    return GitDetectorConfig(
        root_path=common_config['root_path'],
        analyze_commits_count=analyze_commits_count,
        git_repo_path=git_repo_path
    )


def load_api_design_detector_config(config_path: Optional[str] = None) -> ApiDesignDetectorConfig:
    """
    从配置文件加载 ApiDesignDetector 配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则查找默认配置文件
        
    Returns:
        ApiDesignDetectorConfig 实例
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    config_data = _load_config_data(config_path)
    common_config = _parse_common_config(config_data)
    
    codeindex_config = config_data.get('codeindex', {})
    codeindex_db_path = codeindex_config.get('db_path')
    
    api_config = config_data.get('api', {})
    analyze_frameworks = api_config.get('analyze_frameworks')
    
    return ApiDesignDetectorConfig(
        root_path=common_config['root_path'],
        codeindex_db_path=codeindex_db_path,
        languages=common_config['languages'],
        analyze_frameworks=analyze_frameworks
    )


def load_detector_config(
    config_path: Optional[str] = None,
    config_type: Optional[str] = None
) -> Union[StructureDetectorConfig, CodeStyleDetectorConfig, GitDetectorConfig, ApiDesignDetectorConfig]:
    """
    从配置文件加载检测器配置（公共函数，支持多种配置类型）
    
    Args:
        config_path: 配置文件路径，如果为 None 则查找默认配置文件
        config_type: 配置类型，可选值：'structure', 'codestyle', 'git', 'api'，默认为 'structure'
        
    Returns:
        检测器配置实例
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误或配置类型无效
    """
    if config_type is None:
        config_type = 'structure'
    
    if config_type == 'structure':
        return load_structure_detector_config(config_path)
    elif config_type == 'codestyle':
        return load_codestyle_detector_config(config_path)
    elif config_type == 'git':
        return load_git_detector_config(config_path)
    elif config_type == 'api':
        return load_api_design_detector_config(config_path)
    else:
        raise ValueError(f"无效的配置类型: {config_type}，支持的类型: 'structure', 'codestyle', 'git', 'api'")
