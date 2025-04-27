"""
Flask应用模块，提供HTTP API接口
"""

import os
import logging
from flask import Flask, request, jsonify
from services.pdf_service import process_pdf_file
from services.markdown_service import process_markdown_file
from utils.logging_utils import configure_logging

# 配置日志
logger = configure_logging()

# 创建Flask应用
app = Flask(__name__)

@app.route('/process_pdf', methods=['POST'])
def process_pdf():
    """
    处理PDF文件的API接口
    
    请求参数:
        bucket_name: S3桶名
        key: PDF文件的S3对象键
        out_put: 输出目录名
        ak: AWS访问密钥
        sk: AWS秘密访问密钥
        endpoint_url: S3端点URL
        
    返回:
        处理结果的JSON响应
    """
    try:
        # 获取请求参数
        data = request.json
        bucket_name = data.get('bucket_name')
        ak = data.get('ak')
        sk = data.get('sk')
        endpoint_url = data.get('endpoint_url')
        key = data.get('key')
        out_put = data.get('out_put')
        
        # 参数验证
        if not all([bucket_name, ak, sk, endpoint_url, key, out_put]):
            logger.error("缺少必要参数")
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # 处理PDF文件
        result = process_pdf_file(bucket_name, key, out_put, ak, sk, endpoint_url)
        
        if result:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'failed', 'error': 'PDF processing failed'}), 500

    except Exception as e:
        logger.error(f"处理PDF时发生错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_markdown', methods=['POST'])
def process_markdown():
    """
    处理Markdown文件的API接口
    
    请求参数:
        bucket_name: S3桶名
        key: Markdown文件的S3对象键
        
    返回:
        处理结果的JSON响应
    """
    try:
        # 获取请求参数
        data = request.json
        bucket_name = data.get('bucket_name')
        key = data.get('key')
        
        # 参数验证
        if not all([bucket_name, key]):
            logger.error("缺少必要参数")
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # 处理Markdown文件
        result = process_markdown_file(bucket_name, key)
        
        if result:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'failed', 'error': 'Markdown processing failed'}), 500

    except Exception as e:
        logger.error(f"处理Markdown时发生错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_app():
    """启动Flask应用"""
    # 从环境变量获取端口，默认为5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    run_app()
