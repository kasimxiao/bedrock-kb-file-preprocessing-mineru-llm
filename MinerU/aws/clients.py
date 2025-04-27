"""
AWS服务客户端管理模块，提供各种AWS服务的客户端单例
"""

import boto3
from functools import lru_cache
from config import AWS_CONFIG

class AWSClientManager:
    """AWS服务客户端管理器，使用单例模式管理各种AWS服务客户端"""
    
    _instances = {}
    
    @classmethod
    def get_instance(cls):
        """获取AWSClientManager单例"""
        if cls not in cls._instances:
            cls._instances[cls] = cls()
        return cls._instances[cls]
    
    def __init__(self):
        """初始化客户端缓存"""
        self._s3_client = None
        self._bedrock_client = None
        self._dynamodb_resource = None
        self._dynamodb_client = None
    
    @property
    def s3(self):
        """获取S3客户端"""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3')
        return self._s3_client
    
    @property
    def bedrock(self):
        """获取Bedrock客户端"""
        if self._bedrock_client is None:
            self._bedrock_client = boto3.client(
                'bedrock-runtime', 
                region_name=AWS_CONFIG['BEDROCK_REGION']
            )
        return self._bedrock_client
    
    @property
    def dynamodb_resource(self):
        """获取DynamoDB资源"""
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource(
                'dynamodb',
                region_name=AWS_CONFIG['DYNAMODB_REGION']
            )
        return self._dynamodb_resource
    
    @property
    def dynamodb_client(self):
        """获取DynamoDB客户端"""
        if self._dynamodb_client is None:
            self._dynamodb_client = boto3.client(
                'dynamodb',
                region_name=AWS_CONFIG['DYNAMODB_REGION']
            )
        return self._dynamodb_client

# 导出便捷函数
@lru_cache(maxsize=1)
def get_aws_clients():
    """获取AWS客户端管理器单例"""
    return AWSClientManager.get_instance()

def get_s3_client():
    """获取S3客户端"""
    return get_aws_clients().s3

def get_bedrock_client():
    """获取Bedrock客户端"""
    return get_aws_clients().bedrock

def get_dynamodb_resource():
    """获取DynamoDB资源"""
    return get_aws_clients().dynamodb_resource

def get_dynamodb_client():
    """获取DynamoDB客户端"""
    return get_aws_clients().dynamodb_client
