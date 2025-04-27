"""
S3操作相关工具函数
"""

import logging
from urllib.parse import urlparse
from clients import get_s3_client
from config import AWS_CONFIG

logger = logging.getLogger(__name__)

def s3_url_to_cloudfront_url(s3_url):
    """
    将S3 URL转换为CloudFront URL
    
    Args:
        s3_url: S3 URL，格式为s3://bucket/path/to/file
        
    Returns:
        CloudFront URL
    """
    parsed = urlparse(s3_url)
    if parsed.scheme != 's3':
        return s3_url
    
    path = parsed.path.lstrip('/')
    return f"{AWS_CONFIG['CLOUDFRONT_DOMAIN']}/{path}"

def parse_s3_url(s3_url):
    """
    解析S3 URL，返回桶名和对象键
    
    Args:
        s3_url: S3 URL，格式为s3://bucket/path/to/file
        
    Returns:
        (bucket, key)元组
    """
    parsed = urlparse(s3_url)
    if parsed.scheme != 's3':
        raise ValueError(f"不是有效的S3 URL: {s3_url}")
    
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    return bucket, key

def get_object_size(bucket, key):
    """
    获取S3对象的大小
    
    Args:
        bucket: S3桶名
        key: S3对象键
        
    Returns:
        对象大小（字节）
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return response['ContentLength']
    except Exception as e:
        logger.error(f"获取对象大小失败: {str(e)}")
        return 0

def download_s3_object(bucket, key):
    """
    从S3下载对象
    
    Args:
        bucket: S3桶名
        key: S3对象键
        
    Returns:
        对象内容（字节）
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket, Key=key)
        try:
            return response['Body'].read()
        finally:
            # 确保响应体被关闭
            if 'Body' in response and hasattr(response['Body'], 'close'):
                response['Body'].close()
    except Exception as e:
        logger.error(f"下载S3对象失败: {str(e)}")
        return None

def upload_s3_object(content, bucket, key, content_type=None):
    """
    上传对象到S3
    
    Args:
        content: 对象内容（字节或字符串）
        bucket: S3桶名
        key: S3对象键
        content_type: 内容类型，如'text/markdown'
        
    Returns:
        是否上传成功
    """
    try:
        s3_client = get_s3_client()
        
        # 如果content是字符串，转换为字节
        if isinstance(content, str):
            content = content.encode('utf-8')
            
        params = {
            'Body': content,
            'Bucket': bucket,
            'Key': key
        }
        
        if content_type:
            params['ContentType'] = content_type
            
        s3_client.put_object(**params)
        logger.info(f"已上传对象到 s3://{bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"上传对象失败: {str(e)}")
        return False
