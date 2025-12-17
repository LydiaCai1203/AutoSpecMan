"""
CodeIndex 相关工具函数
用于查找数据库、连接客户端等公共功能
"""

from pathlib import Path
from typing import Optional

from codeindex import CodeIndexClient, DatabaseNotFoundError


def find_codeindex_db(root_path: str, db_path: Optional[str] = None) -> Optional[str]:
    """
    自动查找 CodeIndex 数据库路径
    
    Args:
        root_path: 项目根目录路径
        db_path: 如果指定，优先使用此路径
        
    Returns:
        数据库路径，如果未找到返回 None
    """
    root_path_obj = Path(root_path).resolve()
    
    # 如果配置中指定了路径，优先使用
    if db_path:
        db_path_obj = Path(db_path)
        if db_path_obj.is_absolute():
            if db_path_obj.exists():
                return str(db_path_obj)
        else:
            # 相对路径，相对于 root_path
            full_path = root_path_obj / db_path_obj
            if full_path.exists():
                return str(full_path)
    
    # 自动查找：在 root_path 下查找 .codeindex 目录
    codeindex_dir = root_path_obj / '.codeindex'
    if codeindex_dir.exists() and codeindex_dir.is_dir():
        # 查找所有 .db 文件
        db_files = list(codeindex_dir.glob('*.db'))
        if db_files:
            # 返回第一个找到的数据库文件
            return str(db_files[0])
    
    # 在父目录中查找
    parent_codeindex = root_path_obj.parent / '.codeindex'
    if parent_codeindex.exists() and parent_codeindex.is_dir():
        db_files = list(parent_codeindex.glob('*.db'))
        if db_files:
            return str(db_files[0])
    
    return None


def create_codeindex_client(db_path: str) -> CodeIndexClient:
    """
    创建并启动 CodeIndex 客户端
    
    Args:
        db_path: 数据库路径
        
    Returns:
        CodeIndexClient 实例（已启动）
        
    Raises:
        FileNotFoundError: 数据库文件不存在
        RuntimeError: 无法连接数据库
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"CodeIndex 数据库不存在: {db_path}\n"
            f"请先使用 CodeIndex CLI 建立索引：\n"
            f"  node dist/cli/index.js index --root <project_path> --db {db_path}"
        )
    
    try:
        client = CodeIndexClient(db_path)
        client.start()
        return client
    except DatabaseNotFoundError:
        raise FileNotFoundError(f"CodeIndex 数据库不存在: {db_path}")
    except Exception as e:
        raise RuntimeError(f"无法连接 CodeIndex 数据库: {e}")


def get_codeindex_client_or_none(root_path: str, db_path: Optional[str] = None) -> Optional[CodeIndexClient]:
    """
    尝试创建 CodeIndex 客户端，如果失败返回 None（不抛出异常）
    
    Args:
        root_path: 项目根目录路径
        db_path: 数据库路径（可选）
        
    Returns:
        CodeIndexClient 实例或 None
    """
    try:
        found_db_path = find_codeindex_db(root_path, db_path)
        if not found_db_path:
            return None
        return create_codeindex_client(found_db_path)
    except Exception:
        return None

