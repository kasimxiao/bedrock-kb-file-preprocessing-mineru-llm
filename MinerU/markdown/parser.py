"""
Markdown解析模块，提供Markdown文本解析和处理功能
"""

import re
import os
import logging
from aws.s3_utils import parse_s3_url

logger = logging.getLogger(__name__)

def extract_paragraphs_with_images(md_content):
    """
    从Markdown内容中提取包含图片的段落，以Markdown标题(#)作为分段依据
    
    Args:
        md_content: Markdown内容
        
    Returns:
        包含图片的段落列表，每个元素为(段落文本, 图片URL列表)
    """
    # 使用标题(#)作为分段依据
    sections = []
    
    # 添加文档开头到第一个标题之间的内容作为一个段落(如果有)
    first_heading_match = re.search(r'^#+ ', md_content, re.MULTILINE)
    if first_heading_match:
        if first_heading_match.start() > 0:
            sections.append(md_content[:first_heading_match.start()].strip())
    else:
        # 如果没有标题，则整个文档作为一个段落
        sections.append(md_content)
        
    # 提取所有标题及其内容
    heading_matches = list(re.finditer(r'^(#+ .+?)(?=\n#+ |\Z)', md_content, re.MULTILINE | re.DOTALL))
    for match in heading_matches:
        sections.append(match.group(1))
    
    # 过滤出包含图片的段落
    result = []
    for section in sections:
        if not section:  # 跳过空段落
            continue
            
        # 查找图片引用
        image_matches = re.finditer(r'!\[(.*?)\]\((.*?)\)', section)
        image_urls = [match.group(2) for match in image_matches]
        
        if image_urls:
            result.append((section, image_urls))
    return result

def extract_image_references(md_content):
    """
    从Markdown内容中提取所有图片引用
    
    Args:
        md_content: Markdown内容
        
    Returns:
        图片引用列表，每个元素为(alt_text, image_url, 完整匹配)
    """
    pattern = r'!\[(.*?)\]\((.*?)\)'
    matches = list(re.finditer(pattern, md_content))
    
    result = []
    for match in matches:
        alt_text = match.group(1)
        image_url = match.group(2)
        full_match = match.group(0)
        result.append((alt_text, image_url, full_match))
    
    return result

def get_image_path_from_md_path(md_s3_url):
    """
    从Markdown文件的S3路径获取图片目录路径
    
    Args:
        md_s3_url: Markdown文件的S3 URL
        
    Returns:
        图片目录的S3 URL
    """
    bucket, key = parse_s3_url(md_s3_url)
    
    # 获取Markdown文件所在目录
    md_dir = os.path.dirname(key)
    
    # 图片目录为Markdown文件所在目录下的images子目录
    image_dir = f"{md_dir}/images"
    
    return f"s3://{bucket}/{image_dir}"
