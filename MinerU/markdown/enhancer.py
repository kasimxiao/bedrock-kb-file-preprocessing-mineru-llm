"""
Markdown增强模块，提供Markdown内容增强功能
"""

import os
import re
import logging
import concurrent.futures
import threading
import time
import gc
from urllib.parse import urlparse
from config import THREAD_POOL_CONFIG, IMAGE_CONFIG
from aws.s3_utils import s3_url_to_cloudfront_url, parse_s3_url
from image.processor import download_and_convert_image, is_image_processable, is_image_analyzable
from aws.bedrock_utils import analyze_image_with_bedrock
from parser import extract_paragraphs_with_images, get_image_path_from_md_path

logger = logging.getLogger(__name__)

class MarkdownImageEnhancer:
    """Markdown图片增强器，用于处理和增强Markdown文件中的图片引用"""
    
    def __init__(self, md_content, md_s3_url):
        """
        初始化Markdown图片增强器
        
        Args:
            md_content: Markdown文件内容
            md_s3_url: Markdown文件的S3 URL
        """
        self.md_content = md_content
        self.md_s3_url = md_s3_url
    
    def log_thread_info(self, message):
        """
        记录线程信息的辅助函数
        
        Args:
            message: 要记录的消息
        """
        thread_id = threading.get_ident()
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_msg = f"[线程 {thread_id} | {timestamp}] {message}"
        logger.info(log_msg)
    
    def process_image_reference(self, match):
        """
        处理单个图片引用
        
        Args:
            match: 正则表达式匹配对象
            
        Returns:
            处理后的图片引用字符串
        """
        alt_text = match.group(1)
        image_url = match.group(2)

        # 如果已经是CloudFront URL，则不处理
        if image_url.startswith("https://"):
            return match.group(0)
        
        # 获取图片的S3路径
        image_base_dir = get_image_path_from_md_path(self.md_s3_url)
        image_name = os.path.basename(image_url)
        image_s3_url = f"{image_base_dir}/{image_name}"
        
        # 解析图片S3 URL
        image_bucket, image_key = parse_s3_url(image_s3_url)
        
        # 检查图片是否可处理
        if not is_image_processable(image_bucket, image_key):
            # 图片太小，删除引用
            logger.info(f"图片 {image_s3_url} 太小，已删除引用")
            return ""
        
        # 转换为CloudFront URL
        cloudfront_url = s3_url_to_cloudfront_url(image_s3_url)
        
        # 返回更新后的图片引用
        return f"![{alt_text}]({cloudfront_url})"
    
    def process_image_reference_with_logging(self, args):
        """
        处理单个图片引用（带日志记录，用于多线程）
        
        Args:
            args: 参数元组 (match, idx)
            
        Returns:
            (原始引用, 处理后的引用)
        """
        match, idx = args
        
        try:
            # 调用原始处理函数
            result = self.process_image_reference(match)
            return match.group(0), result
        except Exception as e:
            logger.error(f"处理图片引用 #{idx} 时出错: {str(e)}")
            return match.group(0), match.group(0)  # 出错时保持原样
    
    def update_image_references(self):
        """
        更新Markdown内容中的图片引用（使用多线程）
        
        Returns:
            处理后的Markdown内容
        """
        # 使用正则表达式查找所有图片引用
        pattern = r'!\[(.*?)\]\((.*?)\)'
        matches = list(re.finditer(pattern, self.md_content))
        
        if not matches:
            return self.md_content
        
        # 创建一个字典，用于存储原始引用和处理后的引用
        replacements = {}
        
        # 准备任务
        tasks = [(match, idx) for idx, match in enumerate(matches)]
        
        # 使用线程池并行处理图片引用
        with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG['PROCESS']) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self.process_image_reference_with_logging, task): task
                for task in tasks
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_task):
                try:
                    original, replacement = future.result()
                    # 存储原始引用和处理后的引用
                    replacements[original] = replacement
                except Exception as e:
                    logger.error(f"处理图片引用时出错: {str(e)}")
        
        # 替换所有图片引用
        processed_content = self.md_content
        for original, replacement in replacements.items():
            processed_content = processed_content.replace(original, replacement)
        
        return processed_content
    
    def extract_image_info(self, paragraph, image_urls, paragraph_idx):
        """
        从段落中提取图片信息
        
        Args:
            paragraph: 段落文本
            image_urls: 图片URL列表
            paragraph_idx: 段落索引
            
        Returns:
            (修改后的上下文, 图片信息列表)
            图片信息列表中的每个元素为(bucket, key, url, idx)
        """
        # 直接使用当前段落作为上下文
        context_text = paragraph
        modified_context = context_text

        # 收集图片信息
        image_info_list = []
        
        # 遍历：收集图片信息并替换上下文中的图片引用
        for idx, image_url in enumerate(image_urls, 1):
            # 替换上下文中的图片引用为[imageX]标签
            image_tag = f"[image{idx}]"
            pattern = f'!\\[(.*?)\\]\\({re.escape(image_url)}\\)'
            modified_context = re.sub(pattern, image_tag, modified_context)
            
            # 如果是CloudFront URL，则从URL中提取S3路径
            if image_url.startswith("https://"):
                # 从CloudFront URL提取路径部分
                path = urlparse(image_url).path.lstrip('/')
                image_bucket = self.md_s3_url.split('/')[2]  # 从md_s3_url获取桶名
                image_key = path
            else:
                # 获取图片的S3路径
                image_base_dir = get_image_path_from_md_path(self.md_s3_url)
                image_name = os.path.basename(image_url)
                image_s3_url = f"{image_base_dir}/{image_name}"
                image_bucket, image_key = parse_s3_url(image_s3_url)
            
            # 检查图片是否可分析
            if not is_image_analyzable(image_bucket, image_key):
                logger.info(f"图片 {image_url} 太小，跳过理解")
                continue
            
            # 存储图片信息
            image_info_list.append((image_bucket, image_key, image_url, idx))
        
        return modified_context, image_info_list
    
    def extract_image_info_with_logging(self, args):
        """
        从段落中提取图片信息（带日志记录，用于多线程）
        
        Args:
            args: 参数元组 (paragraph, image_urls, paragraph_idx)
            
        Returns:
            (modified_context, image_info_list, paragraph_idx)
        """
        paragraph, image_urls, paragraph_idx = args
        
        try:
            # 调用原始提取函数
            modified_context, image_info_list = self.extract_image_info(paragraph, image_urls, paragraph_idx)
            return modified_context, image_info_list, paragraph_idx
        except Exception as e:
            logger.error(f"提取段落 #{paragraph_idx} 中图片信息时出错: {str(e)}")
            return paragraph, [], paragraph_idx
    
    def download_image_with_logging(self, args):
        """
        下载单个图片（带日志记录，用于多线程）
        
        Args:
            args: 参数元组 (image_info, paragraph_idx)
            
        Returns:
            (图片URL, 索引, base64编码的图片数据, 段落索引)
        """
        image_info, paragraph_idx = args
        bucket, key, url, idx = image_info
        
        try:
            # 调用下载函数
            image_bytes = download_and_convert_image(bucket, key)
            
            if image_bytes:
                return url, idx, image_bytes, paragraph_idx
            else:
                logger.warning(f"下载图片 #{idx} (段落 #{paragraph_idx}) 失败")
                return None
        except Exception as e:
            logger.error(f"下载图片 #{idx} (段落 #{paragraph_idx}) 出错: {str(e)}")
            return None
        finally:
            # 显式调用垃圾回收，帮助释放大型图片数据
            gc.collect()
    
    def analyze_images_with_logging(self, args):
        """
        分析段落中的图片（带日志记录，用于多线程）
        
        Args:
            args: 参数元组 (modified_context, image_base64_list, image_url_to_index, paragraph_idx)
            
        Returns:
            (段落索引, 图片URL到索引的映射, 分析结果)
        """
        modified_context, image_base64_list, image_url_to_index, paragraph_idx = args
        
        try:
            # 使用Bedrock分析所有图片
            understanding_results = analyze_image_with_bedrock(image_base64_list, modified_context)
            
            return paragraph_idx, image_url_to_index, understanding_results
        except Exception as e:
            logger.error(f"分析段落 #{paragraph_idx} 中图片时出错: {str(e)}")
            return paragraph_idx, image_url_to_index, {}
        finally:
            # 清理大型变量以帮助垃圾回收
            del image_base64_list
            
            # 显式调用垃圾回收
            gc.collect()
    
    def add_image_understanding(self, md_content):
        """
        为Markdown中的图片添加理解内容（使用多线程）
        
        Args:
            md_content: 处理后的Markdown内容
            
        Returns:
            添加图片理解后的Markdown内容
        """
        # 提取包含图片的段落
        paragraphs_with_images = extract_paragraphs_with_images(md_content)
        
        if not paragraphs_with_images:
            return md_content
        
        # 创建一个新的Markdown内容
        new_md_content = md_content
        
        # 步骤1：使用多线程提取所有段落中的图片信息
        extract_tasks = [(paragraph, image_urls, idx) for idx, (paragraph, image_urls) in enumerate(paragraphs_with_images)]
        
        # 使用线程池并行提取图片信息
        paragraph_info_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG['EXTRACT']) as executor:
            # 提交所有提取任务
            future_to_task = {
                executor.submit(self.extract_image_info_with_logging, task): task
                for task in extract_tasks
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_task):
                try:
                    modified_context, image_info_list, paragraph_idx = future.result()
                    if image_info_list:  # 只添加有图片的段落
                        paragraph_info_list.append((modified_context, image_info_list, paragraph_idx))
                except Exception as e:
                    logger.error(f"提取图片信息时出错: {str(e)}")
        
        # 清理不再需要的变量
        del extract_tasks
        del paragraphs_with_images
        
        if not paragraph_info_list:
            return md_content
        
        # 步骤2：使用多线程下载所有图片
        all_image_info = []
        for modified_context, image_info_list, paragraph_idx in paragraph_info_list:
            for image_info in image_info_list:
                all_image_info.append((image_info, paragraph_idx))
        
        if not all_image_info:
            return md_content
        
        # 使用线程池并行下载图片
        image_download_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG['DOWNLOAD']) as executor:
            # 分批提交下载任务，避免一次性加载过多图片
            batch_size = IMAGE_CONFIG['MAX_BATCH_SIZE']
            for i in range(0, len(all_image_info), batch_size):
                batch = all_image_info[i:i+batch_size]
                
                # 提交当前批次的下载任务
                future_to_task = {
                    executor.submit(self.download_image_with_logging, task): task
                    for task in batch
                }
                
                # 收集当前批次的结果
                for future in concurrent.futures.as_completed(future_to_task):
                    try:
                        result = future.result()
                        if result:
                            image_download_results.append(result)
                    except Exception as e:
                        logger.error(f"下载图片时出错: {str(e)}")
                
                # 在批次之间进行垃圾回收
                gc.collect()
        
        # 清理不再需要的变量
        del all_image_info
        
        if not image_download_results:
            return md_content
        
        # 按段落组织下载结果
        paragraph_analysis_info = {}
        for url, idx, base64_image, paragraph_idx in image_download_results:
            if paragraph_idx not in paragraph_analysis_info:
                # 查找对应的段落信息
                for modified_context, _, p_idx in paragraph_info_list:
                    if p_idx == paragraph_idx:
                        paragraph_analysis_info[paragraph_idx] = {
                            'modified_context': modified_context,
                            'image_base64_list': [],
                            'image_url_to_index': {}
                        }
                        break
            
            # 添加图片信息
            paragraph_analysis_info[paragraph_idx]['image_base64_list'].append(base64_image)
            paragraph_analysis_info[paragraph_idx]['image_url_to_index'][url] = idx
        
        # 清理不再需要的变量
        del image_download_results
        del paragraph_info_list
        
        if not paragraph_analysis_info:
            return md_content
        
        # 步骤3：使用多线程分析图片
        analysis_tasks = []
        for paragraph_idx, info in paragraph_analysis_info.items():
            if info['image_base64_list']:
                analysis_tasks.append((
                    info['modified_context'],
                    info['image_base64_list'],
                    info['image_url_to_index'],
                    paragraph_idx
                ))
        
        # 清理不再需要的变量
        del paragraph_analysis_info
        
        if not analysis_tasks:
            return md_content
        
        # 使用线程池并行分析图片
        analysis_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_POOL_CONFIG['ANALYZE']) as executor:
            # 提交所有分析任务
            future_to_task = {
                executor.submit(self.analyze_images_with_logging, task): task
                for task in analysis_tasks
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_task):
                try:
                    result = future.result()
                    if result:
                        analysis_results.append(result)
                except Exception as e:
                    logger.error(f"分析图片时出错: {str(e)}")
        
        # 清理不再需要的变量
        del analysis_tasks
        
        if not analysis_results:
            return md_content
        
        # 处理分析结果，更新Markdown内容
        for paragraph_idx, image_url_to_index, understanding_results in analysis_results:
            # 处理每个图片的分析结果
            for image_url, idx in image_url_to_index.items():
                image_key = f"image{idx}"
                
                # 获取当前图片的分析结果
                image_understanding = ""
                if isinstance(understanding_results, dict) and image_key in understanding_results:
                    image_understanding = understanding_results.get(image_key, "")
                
                # 如果分析结果为空，跳过此图片
                if not image_understanding:
                    continue
                
                # 在图片引用后添加理解内容
                pattern = f'!\\[(.*?)\\]\\({re.escape(image_url)}\\)'
                # 转义图片解析内容中的特殊字符，避免正则表达式错误
                safe_understanding = image_understanding.replace('\\', '\\\\')
                replacement = f'![\\1]({image_url})\n\n*图片解析：{safe_understanding}*'
                
                new_md_content = re.sub(pattern, replacement, new_md_content)
        
        # 清理不再需要的变量
        del analysis_results
        
        # 最终垃圾回收
        gc.collect()
        
        return new_md_content
    
    def enhance(self):
        """
        增强Markdown文件，包括更新图片引用和添加图片理解内容
        
        Returns:
            处理后的Markdown内容
        """
        # 步骤1：更新图片引用
        processed_content = self.update_image_references()
        
        # 步骤2：添加图片理解内容
        final_content = self.add_image_understanding(processed_content)
        
        return final_content
