"""
日志工具模块，提供日志配置和辅助函数
"""

import logging
import os
import psutil
import threading
import time
from config import LOGGING_CONFIG

# 配置根日志记录器
def configure_logging():
    """配置全局日志记录器"""
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG['LEVEL']),
        format=LOGGING_CONFIG['FORMAT']
    )
    return logging.getLogger(__name__)

# 创建日志记录器
logger = configure_logging()

def log_memory_usage(message):
    """
    记录当前内存使用情况
    
    Args:
        message: 日志消息前缀
    """
    if not LOGGING_CONFIG['ENABLE_MEMORY_LOGGING']:
        return
        
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    logger.info(f"{message} - 内存使用: {memory_mb:.2f} MB")

def log_thread_info(message):
    """
    记录线程信息的辅助函数
    
    Args:
        message: 要记录的消息
    """
    thread_id = threading.get_ident()
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    log_msg = f"[线程 {thread_id} | {timestamp}] {message}"
    logger.info(log_msg)
