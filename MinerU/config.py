"""
配置文件，包含应用程序所需的全局配置参数
"""

# AWS 服务配置
AWS_CONFIG = {
    "BUCKET_NAME": "wongxiao-bedrock-kb-us-west-2",
    "DYNAMODB_REGION": "us-west-2",
    "BEDROCK_REGION": "us-west-2",
    "BEDROCK_MODEL_ID": "us.amazon.nova-pro-v1:0",  # 可选: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    "CLOUDFRONT_DOMAIN": "https://d2dnhun51f1g71.cloudfront.net"
}

# 图片处理配置
IMAGE_CONFIG = {
    "MIN_SIZE_BYTES": 5120,  # 最小图片尺寸，小于此尺寸的图片引用将被删除（5KB）
    "MIN_UNDERSTANDING_SIZE_BYTES": 10240,  # 最小图片理解尺寸，小于此尺寸的图片不进行理解（10KB）
    "MAX_BATCH_SIZE": 5  # 每批处理的图片数量
}

# 线程池配置
THREAD_POOL_CONFIG = {
    "EXTRACT": 5,  # 提取图片信息的线程池大小
    "DOWNLOAD": 5,  # 下载图片的线程池大小
    "ANALYZE": 2,   # 分析图片的线程池大小，确定所支持的速率
    "PROCESS": 5    # 处理图片引用的线程池大小
}

# API 调用配置
API_CONFIG = {
    "MAX_RETRIES": 10,  # API调用最大重试次数
    "INITIAL_BACKOFF": 1,  # 初始退避时间（秒）
    "MAX_BACKOFF": 60,  # 最大退避时间（秒）
    "MAX_TOKENS": 2000,  # 生成令牌的最大数量
    "TEMPERATURE": 0.1,  # 生成的随机性（0.0表示确定性输出）
    "TOP_P": 0.1  # 核采样参数
}

# 图片理解提示词
PROMPTS = {
    "IMAGE_UNDERSTANDING": """
Analyze the images in this technical document in context and extract information valuable for vector-based knowledge retrieval. Follow these guidelines:
1. Extract: 
   - Technical text/diagram labels
   - Data patterns/trends
   - Key numerical values
   - Domain-specific symbols/notations
   - Contextually relevant visual concepts
   - Maintaining the same language as the context
2. Exclude:
   - Purely decorative elements
   - Generic schematic components
   - Redundant information already in text
   - Low-information-density visuals
Format requirements:
- Return JSON with image filenames as keys
- Use empty strings ("") for non-informative images
- Escape special characters (e.g., " → \")
- Strictly maintain valid JSON syntax
- Detailed description of the contents of the picture
- Maintaining the same language as the context
Example:
{
  "image1": "image1 Image details",
  "image2": "image2 Image details",
  "image3": "No valid information"
}
""",
    "IMAGE_SYSTEM": "You are a technical documentation analysis expert specializing in multimodal content processing. Your task is to systematically analyze images within knowledge base documents, extract semantically meaningful information that enhances searchability in vector databases, while filtering out non-essential decorative elements. Focus on preserving technical specifications, data patterns, critical diagrams, and domain-specific information relevant to potential search queries."
}

# 日志配置
LOGGING_CONFIG = {
    "LEVEL": "INFO",
    "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "ENABLE_MEMORY_LOGGING": False  # 是否启用内存使用日志
}

# DynamoDB配置
DYNAMODB_CONFIG = {
    "TABLE_NAME": "pdf_processing_records"
}

# 文件处理配置
FILE_PROCESSING = {
    "LOCAL_OUTPUT_DIR": "output/",
    "LOCAL_IMAGE_DIR": "output/images/",
    "S3_OUTPUT_PREFIX": "ProcessingFile/"
}
