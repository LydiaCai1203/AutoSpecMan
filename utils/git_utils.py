"""
Git 命令封装工具
提供 Git 命令执行的统一接口
"""

import subprocess
from pathlib import Path
from typing import List, Optional
from utils.logger import logger


def execute_git_command(repo_path: str, command: List[str], timeout: int = 30) -> str:
    """
    执行 Git 命令
    
    Args:
        repo_path: Git 仓库路径
        command: Git 命令参数列表
        timeout: 超时时间（秒）
        
    Returns:
        命令输出结果（字符串），失败返回空字符串
    """
    try:
        result = subprocess.run(
            ['git'] + command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout
        )
        if result.returncode != 0:
            logger.debug(f"Git 命令执行失败: {' '.join(command)}, 错误: {result.stderr}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Git 命令超时: {' '.join(command)}")
        return ""
    except Exception as e:
        logger.debug(f"Git 命令执行异常: {' '.join(command)}, 错误: {e}")
        return ""


def is_git_repo(path: str) -> bool:
    """
    检查路径是否为 Git 仓库
    
    Args:
        path: 路径字符串
        
    Returns:
        如果是 Git 仓库返回 True
    """
    git_dir = Path(path) / '.git'
    return git_dir.exists() and (git_dir.is_dir() or git_dir.is_file())


def get_git_repo_path(start_path: str) -> Optional[str]:
    """
    从指定路径向上查找 Git 仓库根目录
    
    Args:
        start_path: 起始路径
        
    Returns:
        Git 仓库根目录路径，如果未找到返回 None
    """
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if is_git_repo(str(current)):
            return str(current)
        current = current.parent
    
    return None

