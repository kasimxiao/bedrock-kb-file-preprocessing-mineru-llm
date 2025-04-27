"""
内存管理工具模块，提供内存优化和垃圾回收辅助函数
"""

import gc
import logging

logger = logging.getLogger(__name__)

def cleanup_variables(*variables):
    """
    清理变量以帮助垃圾回收
    
    Args:
        *variables: 要清理的变量列表
    """
    for var in variables:
        del var
    
    # 显式调用垃圾回收
    gc.collect()

def force_garbage_collection():
    """
    强制执行垃圾回收
    
    Returns:
        收集的对象数量
    """
    # 禁用垃圾收集器自动运行
    gc.disable()
    
    # 手动运行垃圾收集
    collected = gc.collect()
    
    # 重新启用垃圾收集器
    gc.enable()
    
    logger.debug(f"垃圾回收完成，收集了 {collected} 个对象")
    return collected

def memory_optimized(func):
    """
    内存优化装饰器，在函数执行前后执行垃圾回收
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        # 执行前垃圾回收
        gc.collect()
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            return result
        finally:
            # 执行后垃圾回收
            gc.collect()
    
    return wrapper
