import json
import boto3
from datetime import datetime
import string
import base64
from botocore.exceptions import ClientError
import os.path
import configparser

def run_multi_modal_prompt(bedrock_client, system, messages, model_id):
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": messages,
        "system": system[0]["text"],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p
    }

    response = bedrock_client.invoke_model_with_response_stream(
        modelId=model_id,
        body=json.dumps(body)
    )
    return response.get('body')

def generate_message_stream(system_prompt, user_prompt, assistant_content):
    messages = [{
        "role": "user",
        "content": user_prompt
    },
    {
        "role": "assistant",
        "content": assistant_content
    }]
        
    system = [{ "text": system_prompt}]

    stream = run_multi_modal_prompt(bedrock_client, system, messages, model_id)
    for event in stream:
        try:
            chunk = json.loads(event.get('chunk').get('bytes').decode())
            if chunk.get('type') == 'content_block_delta':
                yield chunk.get('delta', {}).get('text', '')
        except Exception as e:
            print(f"Error processing chunk: {e}")
            continue

bedrock_client = boto3.client(service_name='bedrock-runtime',region_name='us-west-2')
model_id = 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
temperature = 0.1
top_k = 10
top_p = 0.1
max_tokens = 4096
