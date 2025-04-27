import boto3

def rank_documents(query, rerank_model, document):
    bedrock_client = boto3.client(service_name='bedrock-agent-runtime',region_name='us-west-2')

    query = [
        {
            "textQuery":{
                'text': query
            },
            "type": "TEXT"
        }
    ]
    # Get the number of documents to rerank
    num_docs = len(document)
    # Set numberOfResults to the minimum of 5 and the number of documents
    rerankingConfiguration = {
        "bedrockRerankingConfiguration": {
            "modelConfiguration": {
                "modelArn": rerank_model
            },
            "numberOfResults": min(5, num_docs),
        },
        "type": "BEDROCK_RERANKING_MODEL"
    }

    sources = []
    for i in document:
        temp = {
            "inlineDocumentSource": {
                "textDocument":{
                    "text": i['content']
                },
                "type": "TEXT",
            },
            "type": "INLINE"
        }
        sources.append(temp)

    rerank_params = {
        "queries": query,
        "rerankingConfiguration": rerankingConfiguration,
        "sources": sources,
    }

    response = bedrock_client.rerank(**rerank_params)

    print(response)
    return response["results"]
    
