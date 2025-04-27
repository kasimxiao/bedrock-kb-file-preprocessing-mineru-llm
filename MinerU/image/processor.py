"""
图片处理模块，提供图片下载、转换和处理功能
"""

import logging
import io
import gc
from io import BytesIO
from PIL import Image
import base64
from aws.s3_utils import download_s3_object, get_object_size
from config import IMAGE_CONFIG

logger = logging.getLogger(__name__)

def download_and_convert_image(bucket, key):
    """
    从S3下载图片，转换为PNG格式，并返回Base64编码的图片数据
    
    Args:
        bucket: S3桶名
        key: S3对象键
        
    Returns:
        Base64编码的PNG格式图片数据
    """
    try:
        # 下载原始图片数据
        image_bytes = download_s3_object(bucket, key)
        if not image_bytes:
            return None
        
        try:
            # 使用with语句确保资源正确关闭
            with Image.open(BytesIO(image_bytes)) as img:
                with io.BytesIO() as buffer:
                    img.save(buffer, format='PNG')
                    png_bytes = buffer.getvalue()
                    
            # 显式删除大型变量以帮助垃圾回收
            del image_bytes
            
            # 返回Base64编码的图片数据
            return png_bytes
            
        except Exception as e:
            logger.error(f"图片格式转换失败: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"下载图片失败: {str(e)}")
        return None
    finally:
        # 显式调用垃圾回收
        gc.collect()

def is_image_processable(bucket, key):
    """
    检查图片是否可处理（大小是否超过最小阈值）
    
    Args:
        bucket: S3桶名
        key: S3对象键
        
    Returns:
        bool: 图片是否可处理
    """
    image_size = get_object_size(bucket, key)
    return image_size >= IMAGE_CONFIG['MIN_SIZE_BYTES']

def is_image_analyzable(bucket, key):
    """
    检查图片是否可分析（大小是否超过最小理解阈值）
    
    Args:
        bucket: S3桶名
        key: S3对象键
        
    Returns:
        bool: 图片是否可分析
    """
    image_size = get_object_size(bucket, key)
    return image_size >= IMAGE_CONFIG['MIN_UNDERSTANDING_SIZE_BYTES']
