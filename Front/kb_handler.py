import boto3

def retrieve(query_text,kb_id):
    try:
        response = kb_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query_text
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 10,
                    'overrideSearchType':'HYBRID'
                }
            }
        )  
        # 处理检索结果
        results = []
        for retrieval_result in response.get('retrievalResults', []):
            result = {
                'content': retrieval_result.get('content', {}).get('text', ''),
                'score': retrieval_result.get('score', 0),
                'location': retrieval_result.get('location', {}).get('s3Location', {})
            }
            results.append(result)
            
        return results
    except Exception as e:
        print(f"检索错误: {str(e)}")
        return []
    

def retrieve_and_generate(query_text,kb_id,model_arn):
    """
    使用 Bedrock Knowledge Base 的 RetrieveAndGenerate 功能
    检索文档并生成回答
    """
    try:
        response = kb_client.retrieve_and_generate(
            input={
            'text': query_text,
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id,
                    'modelArn': model_arn,
                }
            }
        )
            
        return response['output']['text']
    except Exception as e:
        print(f"检索和生成错误: {str(e)}")
        return None

def list_knowledge_bases():
    try:
        response = agent_client.list_knowledge_bases()
        kbs = []
        for kb in response.get('knowledgeBaseSummaries', []):
            kbs.append({
                'id': kb.get('knowledgeBaseId'),
                'name': kb.get('name', kb.get('knowledgeBaseId')),
                'description': kb.get('description', '')
            })
        return kbs
    except Exception as e:
        print(f"Error listing knowledge bases: {str(e)}")
        return []   

kb_client = boto3.client(service_name='bedrock-agent-runtime',region_name='us-west-2')
agent_client = boto3.client(service_name='bedrock-agent',region_name='us-west-2')
