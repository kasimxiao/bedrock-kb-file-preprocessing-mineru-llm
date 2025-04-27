"""
Markdown处理服务模块，提供Markdown文件处理的高级功能
"""

import logging
import gc
from aws.s3_utils import download_s3_object, upload_s3_object, parse_s3_url
from markdown.enhancer import MarkdownImageEnhancer
from utils.memory_utils import memory_optimized

logger = logging.getLogger(__name__)

@memory_optimized
def process_markdown_file(bucket, key):
    """
    处理Markdown文件，包括更新图片引用和添加图片理解内容
    
    Args:
        bucket: S3桶名
        key: S3对象键
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 构建S3 URL
        md_s3_url = f"s3://{bucket}/{key}"
        
        # 下载Markdown文件
        md_content = download_s3_object(bucket, key)
        if not md_content:
            logger.error("无法读取Markdown文件内容")
            return False
        
        # 解码为文本
        md_content = md_content.decode('utf-8')
        
        # 创建Markdown图片增强器
        enhancer = MarkdownImageEnhancer(md_content, md_s3_url)
        
        # 处理Markdown文件
        final_content = enhancer.enhance()
        
        # 清理不再需要的变量
        del md_content
        del enhancer
        
        # 上传处理后的Markdown文件
        result = upload_s3_object(
            final_content, 
            bucket, 
            key, 
            content_type='text/markdown'
        )
        
        # 清理最终内容
        del final_content
        
        # 显式调用垃圾回收
        gc.collect()

        return result
    
    except Exception as e:
        logger.error(f"处理Markdown文件失败: {str(e)}")
        return False
