"""
全局日志配置模块
使用 loguru 提供统一的日志输出接口
"""

import sys
from pathlib import Path
from loguru import logger


# 移除默认的 handler
logger.remove()

# 配置日志格式
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 添加控制台输出 handler（INFO 级别及以上）
logger.add(
    sys.stderr,
    format=log_format,
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# 添加文件输出 handler（DEBUG 级别及以上）
# 日志文件保存在项目根目录下的 logs 目录
project_root = Path(__file__).parent.parent
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

logger.add(
    logs_dir / "autospecman_{time:YYYY-MM-DD}.log",
    format=log_format,
    level="DEBUG",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    compression="zip",  # 压缩旧日志
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
)

# 导出 logger 实例供其他模块使用
__all__ = ["logger"]

