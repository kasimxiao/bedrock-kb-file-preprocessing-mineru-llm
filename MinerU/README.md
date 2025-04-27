# MinerU

MinerU是一个PDF和Markdown文档处理工具，专注于提取和增强文档中的图片内容。它使用AWS Bedrock服务来分析图片并提供智能描述。

## 功能特点

- PDF文档转换为Markdown格式
- 自动处理和优化Markdown中的图片引用
- 使用AWS Bedrock AI服务分析图片内容
- 为图片添加智能描述和上下文理解
- 高效的并行处理和内存管理

## 项目结构

```
MinerU/
├── api/                  # API接口模块
│   ├── __init__.py
│   └── app.py            # Flask应用和API端点
├── aws/                  # AWS服务交互模块
│   ├── __init__.py
│   ├── bedrock_utils.py  # Bedrock API工具
│   ├── clients.py        # AWS客户端管理
│   ├── dynamodb_utils.py # DynamoDB操作工具
│   └── s3_utils.py       # S3操作工具
├── image/                # 图片处理模块
│   ├── __init__.py
│   └── processor.py      # 图片处理功能
├── markdown/             # Markdown处理模块
│   ├── __init__.py
│   ├── enhancer.py       # Markdown增强功能
│   └── parser.py         # Markdown解析工具
├── services/             # 业务服务模块
│   ├── __init__.py
│   ├── markdown_service.py # Markdown处理服务
│   └── pdf_service.py    # PDF处理服务
├── utils/                # 工具函数模块
│   ├── __init__.py
│   ├── logging_utils.py  # 日志工具
│   └── memory_utils.py   # 内存管理工具
├── config.py             # 配置文件
├── main.py               # 主程序入口
└── requirements.txt      # 依赖包列表
```

## 安装

1. 克隆仓库:
```bash
git clone <repository-url>
cd MinerU
```

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 配置AWS凭证:
确保您的AWS凭证已正确配置，可以通过环境变量、AWS配置文件或IAM角色提供。

## 使用方法

### 启动服务

```bash
python main.py
```

### API端点

#### 处理PDF文件

```
POST /process_pdf
```

请求体:
```json
{
  "bucket_name": "your-s3-bucket",
  "key": "path/to/your/file.pdf",
  "out_put": "output-directory",
  "ak": "your-access-key",
  "sk": "your-secret-key",
  "endpoint_url": "https://s3.region.amazonaws.com"
}
```

#### 处理Markdown文件

```
POST /process_markdown
```

请求体:
```json
{
  "bucket_name": "your-s3-bucket",
  "key": "path/to/your/file.md"
}
```

## 配置

配置参数位于`config.py`文件中，包括:

- AWS服务配置
- 图片处理配置
- 线程池配置
- API调用配置
- 提示词配置
- 日志配置

## 依赖

- Flask: Web框架
- Boto3: AWS SDK
- Pillow: 图片处理
- psutil: 系统资源监控
- magic_pdf: PDF处理库(项目内部依赖)
