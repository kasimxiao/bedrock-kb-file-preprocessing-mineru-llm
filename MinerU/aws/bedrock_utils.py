"""
Bedrock API调用相关工具函数
"""

import json
import logging
import re
import time
import random
import gc
from botocore.exceptions import ClientError
from clients import get_bedrock_client
from config import AWS_CONFIG, API_CONFIG, PROMPTS

logger = logging.getLogger(__name__)

class BedrockAPIError(Exception):
    """Bedrock API调用错误"""
    pass

class RetryableAPIError(BedrockAPIError):
    """可重试的API错误"""
    pass

def analyze_image_with_bedrock(image_base64_list, context_text):
    """
    使用Bedrock Converse接口分析多张图片，支持自动重试
    
    Args:
        image_base64_list: Base64编码的图片数据列表
        context_text: 上下文文本
        
    Returns:
        图片分析结果，JSON格式；遇到错误或重试超过上限时返回空字符串
    """
    try:
        # 构建用户消息
        user_content = [{
            "text": f"上下文内容：\n{context_text}\n\n{PROMPTS['IMAGE_UNDERSTANDING']}"
        }]
        
        # 添加图片到用户消息
        valid_images = 0
        for i, base64_image in enumerate(image_base64_list, 1):
            if not base64_image:
                continue
                
            img_index = f'image{i}'
            user_content.append({"text": img_index})
            
            try:
                user_content.append({
                    "image": {
                        "format": "png",
                        "source": {"bytes": base64_image}
                    }
                })
                valid_images += 1
            except Exception as img_e:
                logger.error(f"添加图片 {img_index} 到请求时出错: {str(img_e)}")
        
        # 如果没有有效的图片，返回空字符串
        if valid_images == 0:
            logger.warning("没有有效的图片可以处理")
            return ""
        
        # 构建完整请求
        messages = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": [{"text": "{"}]}
        ]
        
        system = [{"text": PROMPTS['IMAGE_SYSTEM']}]
        
        inference_config = {
            "maxTokens": API_CONFIG['MAX_TOKENS'],
            "temperature": API_CONFIG['TEMPERATURE'],
            "topP": API_CONFIG['TOP_P']
        }
        
        return _call_bedrock_with_retry(
            messages=messages,
            system=system,
            inference_config=inference_config
        )
        
    except Exception as e:
        logger.error(f"图片分析过程中发生未预期错误: {str(e)}")
        return ""
        
    finally:
        # 显式调用垃圾回收
        gc.collect()

def _call_bedrock_with_retry(messages, system, inference_config):
    """
    调用Bedrock API，支持自动重试
    
    Args:
        messages: 消息列表
        system: 系统提示
        inference_config: 推理配置
        
    Returns:
        API响应结果，遇到错误或重试超过上限时返回空字符串
    """
    # 可重试的错误类型
    retryable_errors = [
        'ThrottlingException', 'ServiceUnavailableException', 'InternalServerException',
        'TooManyRequestsException', 'ProvisionedThroughputExceededException',
        'RequestLimitExceeded', 'LimitExceededException', 'Throttling', 'RequestThrottled'
    ]
    
    # 实现重试逻辑
    retry_count = 0
    backoff_time = API_CONFIG['INITIAL_BACKOFF']
    
    while retry_count <= API_CONFIG['MAX_RETRIES']:
        try:
            # 调用Bedrock API
            response = get_bedrock_client().converse(
                modelId=AWS_CONFIG['BEDROCK_MODEL_ID'],
                messages=messages,
                system=system,
                inferenceConfig=inference_config
            )
            
            # 解析响应
            response_content = '{' + response['output']['message']['content'][0]['text']
            
            # 尝试解析JSON响应
            try:
                return json.loads(response_content)
            except json.JSONDecodeError:
                # 尝试提取JSON部分
                json_match = re.search(r'({.*})', response_content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                logger.warning("无法从响应中提取JSON格式")
                return ""
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = str(e)
            
            # 检查是否是可重试的错误
            if (error_code in retryable_errors or 
                any(err in error_message for err in retryable_errors)):
                if retry_count < API_CONFIG['MAX_RETRIES']:
                    # 计算退避时间（指数退避 + 随机抖动）
                    jitter = random.uniform(0, 0.1 * backoff_time)
                    sleep_time = backoff_time + jitter
                    
                    logger.warning(f"遇到限流错误: {error_message}. 重试 {retry_count+1}/{API_CONFIG['MAX_RETRIES']}, 等待 {sleep_time:.2f}秒")
                    time.sleep(sleep_time)
                    
                    # 增加退避时间（指数增长）
                    backoff_time = min(backoff_time * 2, API_CONFIG['MAX_BACKOFF'])
                    retry_count += 1
                    continue
            
            logger.error(f"Bedrock API调用失败: {error_message}")
            return ""
            
        except Exception as e:
            error_message = str(e)
            
            # 检查是否是可能的限流错误
            if any(err in error_message.lower() for err in ['throttl', 'limit exceeded', 'too many requests']):
                if retry_count < API_CONFIG['MAX_RETRIES']:
                    jitter = random.uniform(0, 0.1 * backoff_time)
                    sleep_time = backoff_time + jitter
                    
                    logger.warning(f"可能的限流错误: {error_message}. 重试 {retry_count+1}/{API_CONFIG['MAX_RETRIES']}, 等待 {sleep_time:.2f}秒")
                    time.sleep(sleep_time)
                    
                    backoff_time = min(backoff_time * 2, API_CONFIG['MAX_BACKOFF'])
                    retry_count += 1
                    continue
            
            logger.error(f"调用Bedrock API失败: {error_message}")
            return ""
        
    # 如果所有重试都失败
    logger.error(f"达到最大重试次数 ({API_CONFIG['MAX_RETRIES']})，返回空结果")
    return ""
