"""
主程序入口模块
"""

import logging
from api.app import run_app
from utils.logging_utils import configure_logging

# 配置日志
logger = configure_logging()

def main():
    """主程序入口函数"""
    logger.info("启动MinerU服务...")
    run_app()

if __name__ == "__main__":
    main()
