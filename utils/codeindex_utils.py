"""
CodeIndex 相关工具函数
用于查找数据库、连接客户端等公共功能
使用单例模式管理客户端连接，确保同一数据库路径只创建一个客户端实例
"""

import threading
from pathlib import Path
from typing import Optional, Dict

from codeindex import CodeIndexClient, DatabaseNotFoundError


class CodeIndexClientManager:
    """CodeIndex 客户端管理器（单例模式）"""
    
    _instance: Optional['CodeIndexClientManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """初始化管理器"""
        self._clients: Dict[str, CodeIndexClient] = {}
        self._client_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'CodeIndexClientManager':
        """
        获取单例实例（线程安全）
        
        Returns:
            CodeIndexClientManager 实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _normalize_path(self, db_path: str) -> str:
        """
        规范化数据库路径（用于作为字典 key）
        
        Args:
            db_path: 数据库路径
            
        Returns:
            规范化的绝对路径字符串
        """
        return str(Path(db_path).resolve())
    
    def get_client(self, db_path: str) -> CodeIndexClient:
        """
        获取或创建 CodeIndex 客户端（单例）
        
        Args:
            db_path: 数据库路径
            
        Returns:
            CodeIndexClient 实例（已启动）
            
        Raises:
            FileNotFoundError: 数据库文件不存在
            RuntimeError: 无法连接数据库
        """
        normalized_path = self._normalize_path(db_path)
        
        with self._client_lock:
            if normalized_path in self._clients:
                client = self._clients[normalized_path]
                try:
                    if not hasattr(client, '_db') or client._db is None:
                        raise RuntimeError("客户端已关闭")
                    return client
                except Exception:
                    del self._clients[normalized_path]
            
            if not Path(db_path).exists():
                raise FileNotFoundError(
                    f"CodeIndex 数据库不存在: {db_path}\n"
                    f"请先使用 CodeIndex CLI 建立索引：\n"
                    f"  node dist/cli/index.js index --root <project_path> --db {db_path}"
                )
            
            try:
                client = CodeIndexClient(db_path)
                client.start()
                self._clients[normalized_path] = client
                return client
            except DatabaseNotFoundError:
                raise FileNotFoundError(f"CodeIndex 数据库不存在: {db_path}")
            except Exception as e:
                raise RuntimeError(f"无法连接 CodeIndex 数据库: {e}")
    
    def get_client_or_none(self, db_path: Optional[str]) -> Optional[CodeIndexClient]:
        """
        尝试获取客户端，如果失败返回 None（不抛出异常）
        
        Args:
            db_path: 数据库路径（如果为 None 则返回 None）
            
        Returns:
            CodeIndexClient 实例或 None
        """
        if db_path is None:
            return None
        
        try:
            return self.get_client(db_path)
        except Exception:
            return None
    
    def close_client(self, db_path: str) -> bool:
        """
        关闭指定数据库路径的客户端
        
        Args:
            db_path: 数据库路径
            
        Returns:
            如果成功关闭返回 True，如果客户端不存在返回 False
        """
        normalized_path = self._normalize_path(db_path)
        
        with self._client_lock:
            if normalized_path in self._clients:
                try:
                    client = self._clients[normalized_path]
                    client.close()
                except Exception:
                    pass  # 忽略关闭时的错误
                del self._clients[normalized_path]
                return True
            return False
    
    def close_all(self):
        """关闭所有客户端连接"""
        with self._client_lock:
            for db_path, client in list(self._clients.items()):
                try:
                    client.close()
                except Exception:
                    pass  # 忽略关闭时的错误
            self._clients.clear()
