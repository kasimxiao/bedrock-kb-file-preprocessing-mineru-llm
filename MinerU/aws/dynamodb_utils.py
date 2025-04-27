"""
DynamoDB操作相关工具函数
"""

import logging
from datetime import datetime
from clients import get_dynamodb_resource
from config import DYNAMODB_CONFIG

logger = logging.getLogger(__name__)

def update_processing_status(file_name, status):
    """
    更新DynamoDB中的文件处理记录状态
    
    Args:
        file_name: 文件名，作为唯一键
        status: 新的处理状态
    
    Returns:
        bool: 操作是否成功
    """
    try:
        table = get_dynamodb_resource().Table(DYNAMODB_CONFIG['TABLE_NAME'])
        current_time = datetime.now().isoformat()
        
        table.update_item(
            Key={
                'file_name': file_name
            },
            UpdateExpression='SET updated_at = :updated_at, #status = :status',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':updated_at': current_time,
                ':status': status
            }
        )
        logger.info(f"已更新 DynamoDB 记录 {file_name} 的状态为: {status}")
        return True
    except Exception as e:
        logger.error(f"更新 DynamoDB 记录失败: {str(e)}")
        return False
