import requests
from requests.exceptions import Timeout, RequestException
import json
from urllib.parse import unquote
import os
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# 全局配置变量
TABLE_NAME = 'pdf_processing_records'
API_URL = "http://xx.xx.xx.xx:5000/process_pdf"
BUCKET_NAME = ""
AK = ""
SK = ""
REGION = ""
ENDPOINT_URL = f"https://s3.{REGION}.amazonaws.com"

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb',region_name=REGION )

def ensure_table_exists():
    """
    确保 DynamoDB 表存在，如果不存在则创建
    """
    try:
        # 检查表是否存在
        dynamodb.Table(TABLE_NAME).table_status
        return dynamodb.Table(TABLE_NAME)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # 表不存在，创建表
            print(f"表 {TABLE_NAME} 不存在，正在创建...")
            table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {
                        'AttributeName': 'file_name',
                        'KeyType': 'HASH'  # 分区键
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'file_name',
                        'AttributeType': 'S'  # 字符串类型
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            
            # 等待表创建完成
            table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
            return table
        else:
            # 其他错误
            print(f"检查表时发生错误: {str(e)}")
            raise

# 确保表存在并获取表引用
table = ensure_table_exists()

def create_dynamodb_record(file_name):
    """
    在 DynamoDB 中创建或更新文件处理记录
    
    Args:
        file_name (str): 文件名，作为唯一键
    
    Returns:
        tuple: (bool, str) - (操作是否成功, 记录状态)
    """
    current_time = datetime.now().isoformat()
    
    try:
        # 查询是否已存在相同 file_name 的记录
        response = table.query(
            KeyConditionExpression=Key('file_name').eq(file_name)
        )
        if response['Items']:
            # 如果记录已存在，检查状态
            existing_record = response['Items'][0]
            existing_status = existing_record.get('status', '')
            
            # 如果状态为"处理成功"，则不做任何处理
            if existing_status == '处理成功':
                print(f"记录 {file_name} 已存在且状态为'处理成功'，跳过处理")
                return True, '处理成功'
            
            # 如果记录已存在但状态不是"处理成功"，则更新
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
                    ':status': '上传成功'
                }
            )
            print(f"已更新 DynamoDB 记录: {file_name}")
            return True, '上传成功'
        else:
            # 如果记录不存在，则创建新记录
            table.put_item(
                Item={
                    'file_name': file_name,
                    'created_at': current_time,
                    'updated_at': current_time,
                    'status': '上传成功'
                }
            )
            print(f"已创建 DynamoDB 记录: {file_name}")
            return True, '上传成功'
    except Exception as e:
        print(f"创建/更新 DynamoDB 记录失败: {str(e)}")
        return False

def update_dynamodb_record(file_name, status):
    """
    更新 DynamoDB 中的文件处理记录状态
    
    Args:
        file_name (str): 文件名，作为唯一键
        status (str): 新的处理状态
    """
    current_time = datetime.now().isoformat()
    
    try:
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
        print(f"已更新 DynamoDB 记录 {file_name} 的状态为: {status}")
    except Exception as e:
        print(f"更新 DynamoDB 记录失败: {str(e)}")

def process_pdf_with_timeout(url, params, timeout=10):
    """
    发送POST请求处理PDF文件，设置超时时间
    
    Args:
        url (str): API端点URL
        params (dict): 请求参数
        timeout (int): 超时时间（秒）
    
    Returns:
        dict: 响应结果
    """
    try:
        # 发送POST请求，设置超时时间
        response = requests.post(
            url,
            json=params,
            timeout=timeout  # 设置超时时间为10秒
        )
        response.raise_for_status()
        return response.json()
    
    except Timeout:
        # 处理超时异常
        print(f"文档处理已提交，等待后端服务处理")
        return {"sueecss": "文档处理提交成功", "message": f"文档处理已提交，等待后端服务处理"}
    
    except RequestException as e:
        # 处理其他请求异常
        print(f"请求发生错误: {str(e)}")
        return {"error": "request_error", "message": str(e)}
    
    except json.JSONDecodeError:
        # 处理JSON解析错误
        print("响应内容不是有效的JSON格式")
        return {"error": "invalid_json", "message": "Response is not valid JSON"}
    
    except Exception as e:
        # 处理其他异常
        print(f"发生未知错误: {str(e)}")
        return {"error": "unknown_error", "message": str(e)}


def extract_path(file_key):
    # 去掉开头的 'SourceFile/'
    if file_key.startswith('SourceFile/'):
        path = file_key[11:]  # 11 是 'SourceFile/' 的长度
    else:
        return ''
    
    # 查找第一个 '/' 的位置
    first_slash = path.find('/')
    if first_slash == -1:  # 如果没有找到 '/'，返回空字符串
        return ''
        
    # 提取到最后一个 '/' 之前的内容
    last_slash = path.rfind('/')
    result = path[:last_slash]
    
    return result

def lambda_handler(event, context):
    global BUCKET_NAME
    
    # 从事件中获取存储桶名称
    BUCKET_NAME = event['Records'][0]['s3']['bucket']['name']
    
    # 文件路径+名称
    file_key = event['Records'][0]['s3']['object']['key'].replace('+',' ')

    file_key = unquote(file_key)
    file_path = extract_path(file_key)
    
    file_name = file_key
    # 创建或更新 DynamoDB 记录，并获取操作结果和记录状态
    record_created, record_status = create_dynamodb_record(file_name)
    
    # 如果记录状态为"处理成功"，则不做任何处理，直接返回
    if record_status == '处理成功':
        print(f"文件 {file_name} 已处理成功，跳过处理")
        return {
            'statusCode': 200,
            'body': {"message": "文件已处理成功，跳过处理"}
        }

    # 请求参数，使用全局变量
    request_params = {
        "bucket_name": BUCKET_NAME,
        "ak": AK,
        "sk": SK,
        "endpoint_url": ENDPOINT_URL,
        "key": file_key,
        "out_put": file_path
    }
    
    # 发送请求，使用全局API_URL
    result = process_pdf_with_timeout(API_URL, request_params)
    
    # 处理响应结果
    if "error" in result:
        print(f"处理失败: {result['message']}")
        # 如果处理失败，更新记录状态
        if record_created:
            update_dynamodb_record(file_name, '提交转换失败')
    else:
        # 如果处理成功，更新记录状态
        if record_created and "sueecss" in result:
            update_dynamodb_record(file_name, '转换处理中')
    
    # 由于代码被注释，返回一个默认响应
    return {
        'statusCode': 200,
        'body': {"message": "文件已上传成功，等待处理"}
    }
