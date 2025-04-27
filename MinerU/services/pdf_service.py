"""
PDF处理服务模块，提供PDF文件处理的高级功能
"""

import os
import logging
import gc
from magic_pdf.data.data_reader_writer import S3DataReader, S3DataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
from utils.memory_utils import memory_optimized
from aws.dynamodb_utils import update_processing_status
from markdown_service import process_markdown_file
from config import FILE_PROCESSING

logger = logging.getLogger(__name__)

@memory_optimized
def process_pdf_file(bucket_name, key, out_put, ak, sk, endpoint_url):
    """
    处理PDF文件，转换为Markdown并增强图片
    
    Args:
        bucket_name: S3桶名
        key: PDF文件的S3对象键
        out_put: 输出目录名
        ak: AWS访问密钥
        sk: AWS秘密访问密钥
        endpoint_url: S3端点URL
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 记录文件名，用于更新DynamoDB
        file_name = key
        
        # 初始化S3读写器
        reader = S3DataReader('', bucket_name, ak, sk, endpoint_url)
        writer = S3DataWriter('', bucket_name, ak, sk, endpoint_url)
        image_writer = S3DataWriter(f'{FILE_PROCESSING["S3_OUTPUT_PREFIX"]}{out_put}/images', bucket_name, ak, sk, endpoint_url)
        md_writer = S3DataWriter(f'{FILE_PROCESSING["S3_OUTPUT_PREFIX"]}{out_put}', bucket_name, ak, sk, endpoint_url)

        # 设置本地目录
        local_image_dir = FILE_PROCESSING["LOCAL_IMAGE_DIR"]
        local_md_dir = FILE_PROCESSING["LOCAL_OUTPUT_DIR"]
        image_dir = os.path.basename(local_image_dir)

        # 设置PDF文件路径
        pdf_file_name = f"s3://{bucket_name}/{key}"
        name_without_suff = os.path.basename(pdf_file_name).split(".")[0]

        logger.info(f"开始处理PDF文件: {pdf_file_name}")
        
        try:
            # 读取PDF内容
            pdf_bytes = reader.read(pdf_file_name)
    
            # 创建数据集实例
            ds = PymuDocDataset(pdf_bytes)
            
            # 处理完成后释放PDF字节数据
            del pdf_bytes
            
            # 处理PDF
            logger.info(f"分类PDF处理方法")
            if ds.classify() == SupportedPdfParseMethod.OCR:
                logger.info(f"使用OCR模式处理PDF")
                infer_result = ds.apply(doc_analyze, ocr=True)
                pipe_result = infer_result.pipe_ocr_mode(image_writer)
            else:
                logger.info(f"使用文本模式处理PDF")
                infer_result = ds.apply(doc_analyze, ocr=False)
                pipe_result = infer_result.pipe_txt_mode(image_writer)
    
            # 生成结果文件
            logger.info(f"生成结果文件")
            infer_result.draw_model(os.path.join(local_md_dir, f"{name_without_suff}_model.pdf"))
            model_inference_result = infer_result.get_infer_res()
            pipe_result.draw_layout(os.path.join(local_md_dir, f"{name_without_suff}_layout.pdf"))
            pipe_result.draw_span(os.path.join(local_md_dir, f"{name_without_suff}_spans.pdf"))
            pipe_result.dump_md(md_writer, f"{name_without_suff}.md", image_dir)
            
            # 释放大型对象以帮助垃圾回收
            del infer_result
            del model_inference_result
            
            # 显式调用垃圾回收
            gc.collect()
        except Exception as e:
            logger.error(f"处理PDF时发生错误: {str(e)}")
            update_processing_status(file_name, '处理失败-转MD')
            return False
        
        # 开始MD优化
        # 更新DynamoDB状态为处理中
        update_processing_status(file_name, '图片转换中')
        
        # 处理Markdown文件中的图片
        md_file_path = f"{FILE_PROCESSING['S3_OUTPUT_PREFIX']}{out_put}/{name_without_suff}.md"
        result = process_markdown_file(bucket_name, md_file_path)
        
        if result:
            # 更新DynamoDB状态为处理成功
            update_processing_status(file_name, '处理成功')
        else:
            update_processing_status(file_name, '处理失败-转图片')
            return False
        
        # 获取其他处理结果
        logger.info(f"获取其他处理结果")
        content_list_content = pipe_result.get_content_list(image_dir)
        middle_json_content = pipe_result.get_middle_json()
        
        # 释放大型对象以帮助垃圾回收
        del pipe_result
        del content_list_content
        del middle_json_content
        
        # 显式调用垃圾回收
        gc.collect()
        
        logger.info(f"PDF处理成功: {file_name}")
        return True

    except Exception as e:
        logger.error(f"处理PDF时发生错误: {str(e)}")
        update_processing_status(file_name, '处理失败-转MD')
        return False
