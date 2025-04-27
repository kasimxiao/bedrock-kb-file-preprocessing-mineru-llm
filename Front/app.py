import streamlit as st
from claude_handler import generate_message_stream
from kb_handler import retrieve, list_knowledge_bases
from rank_handler import rank_documents
import re
import os

# 全局配置
LLM_MODEL = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
RERANK_MODEL = 'arn:aws:bedrock:us-west-2::foundation-model/cohere.rerank-v3-5:0'

# 用户认证配置
USERNAME = "admin"
PASSWORD = "pwd123"


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "pwd" not in st.session_state:
        st.session_state.pwd = ""

def login():
    st.title("登录系统")
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    if st.button("登录"):
        if username == USERNAME and (password == PASSWORD):
            st.session_state.pwd = password
            st.session_state.authenticated = True
            st.success("登录成功！")
            st.rerun()
        else:
            st.error("用户名或密码错误！")

def replace_last_extension(file_path, new_extension):
    # 分离文件路径和文件名
    file_dir, file_name = os.path.split(file_path)
    # 分离最后一个扩展名
    base_name, old_extension = os.path.splitext(file_name)
    # 构建新的文件名
    new_file_name = f"{base_name}.{new_extension}"
    # 构建新的文件路径
    new_file_path = os.path.join(file_dir, new_file_name)
    # 重命名文件
    os.rename(file_path, new_file_path)
    return new_file_path

def main():
    st.set_page_config(layout="wide")
    initialize_session_state()

    # 检查用户是否已登录
    if not st.session_state.authenticated:
        login()
        return

    # 侧边栏配置
    with st.sidebar:
        st.title("配置面板")
        
        # 添加退出按钮
        if st.button("退出登录"):
            st.session_state.pwd = ""  # 重置密码
            st.session_state.authenticated = False
            st.rerun()
        
        try:
            # 获取知识库列表
            knowledge_bases = list_knowledge_bases()
            if st.session_state.pwd == PASSWORD: 
                # 山河智能用户可以看到所有知识库
                kb_options = {f"{kb['description']}": kb['id'] for kb in knowledge_bases}
            else:
                # 未知用户不显示任何知识库
                kb_options = {}
            
            # 知识库选择
            selected_kb_name = st.selectbox(
                '选择知识库',
                options=list(kb_options.keys()),
                index=None,
                placeholder="请选择知识库..."
            )

            # 问题改写开关
            enable_rewrite = st.checkbox("启用问题改写", value=True)
            enable_rerank = st.checkbox("启用召回重排", value=True)
            # 新增检索原文输出选项
            retrieve_original = st.checkbox("检索原文输出", value=False, help="勾选后将使用Claude优化格式并保留原文内容")

        except Exception as e:
            st.error(f'加载知识库失败: {str(e)}')
            return

    # 主界面
    st.title('智能知识库检索系统')

    # 显示聊天历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    # 问题输入
    if prompt := st.chat_input("请输入您的问题...", key="user_input", disabled=not selected_kb_name):
        # 添加用户问题到聊天历史
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # try:
        with st.chat_message("assistant"):
            with st.spinner('处理中...'):
                kb_id = kb_options[selected_kb_name]
                query = prompt
                query_write = query
                
                if enable_rewrite:
                    # 1. 问题改写
                    system_prompt = ''
                  
                    rewrite_prompt = '''
                    你是一个非常资深的知识库查询处理专家，当面对用户咨询时，基于用户的<query>进行优化，理解用户真实意图，将问题进行改写，使问题描述更加清晰，更容易理解，不要随意补充环境和场景，不需要反问客户，输出一个最为贴近用户意图的提问方式，不需要有多余的内容输出，同时要判断<query>语言，以相同语言进行输出
                    <query>%s</query>
                    '''

                    assistant_content = '改写后问题：'
                    
                    # 创建一个空容器用于问题改写的流式输出
                    st.write("🔄 改写后的问题/Rewritten questions：")
                    rewrite_placeholder = st.empty()
                    query_write = ""
                    # 使用流式生成进行问题改写
                    for chunk in generate_message_stream(system_prompt, rewrite_prompt % query, assistant_content):
                        query_write += chunk
                        rewrite_placeholder.markdown(query_write + "▌")
                    
                    # 最终显示完整的改写问题（去除光标）
                    rewrite_placeholder.markdown(query_write)

                # 2. 向量检索
                query_results = retrieve(query_write, kb_id)
                if not query_results:
                    response = "未找到相关信息，请尝试更换关键词或更详细地描述您的问题。No information found, try changing keywords or describing your problem in more detail."
                    st.error(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    return
                

                # 3. 重排序
                content_list = []
                references = []
                images_list = []
                try:
                    if enable_rerank:
                        rerank_result = rank_documents(query_write, RERANK_MODEL, query_results)
                        print(f'rerank_result:{rerank_result}')

                        for result in rerank_result:
                            # 过滤掉相关性得分低于0.3的结果
                            if result['relevanceScore'] < 0.3:
                                print(f"Filtered out result with score: {result['relevanceScore']}")
                                continue
                                
                            idx = int(result['index'])
                            content = {'content':query_results[idx]['content']}
                            content_list.append(content)
                            images_list = []
                            pattern = r'!\[.*?\]\((.*?)\)'
                            images_list=re.findall(pattern, query_results[idx]['content'])
                            location = query_results[idx]['location']['uri']
                
                            references.append({
                                'location': location,
                                'score': result['relevanceScore'],
                                'images': images_list
                            })

                except Exception as e:
                    pass
                
                if len(content_list) == 0:
                    for result in query_results:
                        # idx = int(result['index'])
                        content = {'content':result['content']}
                        content_list.append(content)

                        images_list = []
                        pattern = r'!\[.*?\]\((.*?)\)'
                        images_list=re.findall(pattern, result['content'])

                        location = result['location']['uri']

                        references.append({
                            'location': location,
                            'score': result['score'],
                            'images': images_list
                        })


                # 4. 生成回答
                if retrieve_original and len(references) > 0:
                    # 检索原文输出模式：取相似度最高的一条原文
                    # 找到相似度最高的文档
                    highest_score_ref = max(references, key=lambda x: x['score'])
                    highest_score_idx = references.index(highest_score_ref)
                    original_content = content_list[highest_score_idx]['content']
                    print(original_content)
                    # 使用Claude进行格式调整，而不是总结
                    st.markdown("### 格式优化后的原文内容")
                    
                    system_prompt = ''
                    format_prompt = '''
                    You are a professional document format optimization assistant. Your task is to filter out invalid information based on the retrieved knowledge base content, retain valid information, and ensure that image addresses and their positions in the content are accurate.
                    Please follow these guidelines:
                    Carefully analyze the user's <query>, extract relevant paragraph information from <content>, and output the original content
                    Optimize paragraph formatting, ensuring appropriate line breaks and paragraph separation
                    Ensure output image names are SHA-256 64 hexadecimal characters, exactly matching the original text
                    Maintain the original language of the text
                    Do not add any content or explanations not in the original text
                    If there are obvious formatting issues, you may correct them
                    Preserve the original title structure
                    User query: <query>%s</query>
                    Knowledge base content: <content>%s</content>
                    
                    '''
                    assistant_content = ''
                    
                    # 创建一个空容器用于格式优化后的原文流式输出
                    response_placeholder = st.empty()
                    formatted_response = ""
                    
                    # 使用流式生成
                    for chunk in generate_message_stream(system_prompt, format_prompt % (query_write, '\n'.join(original_content)), assistant_content):
                        formatted_response += chunk
                        # 更新显示的内容
                        response_placeholder.markdown(formatted_response + "▌")

                    # 由于LLM输出SHA-256 64字符长度图片名称非常不稳定，因此需要需要个特殊出用引用图片替换LLM输出中的图片地址
                    # 修复模型输出中可能不完整的图片URL
                    corrected_response = formatted_response
                
                    # 直接使用highest_score_ref中的images_list
                    if highest_score_ref['images']:
                        # 查找markdown格式的图片引用: ![alt](url)
                        img_pattern = r'!\[(.*?)\]\((.*?)\)'
                        img_matches = re.findall(img_pattern, formatted_response)
                        
                        # 按顺序替换图片URL
                        if len(img_matches) > 0 and len(highest_score_ref['images']) > 0:
                            # 确保不会超出图片列表范围
                            for i, (alt_text, img_url) in enumerate(img_matches):
                                if i < len(highest_score_ref['images']):
                                    # 直接使用引用中对应位置的完整URL进行替换
                                    corrected_response = corrected_response.replace(
                                        f'![{alt_text}]({img_url})', 
                                        f'![{alt_text}]({highest_score_ref["images"][i]})'
                                    )
                    
                    # 最终显示修正后的完整内容（去除光标）
                    response_placeholder.markdown(corrected_response)
                    formatted_response = corrected_response
        

                    # 显示来源信息
                    st.markdown("---")
                    st.markdown("### 来源")
                    file_name = highest_score_ref['location'].split('/')[-1]
                    file_url = highest_score_ref['location']
                    score = highest_score_ref['score']
                    st.markdown(f"📄 **文件名**: [{file_name}]({file_url})  \n💯 **相似度**: {score:.2f}")
                    
                    # 添加到聊天历史
                    history_content = f"### 格式优化后的原文内容\n{corrected_response}\n\n---\n### 来源\n"
                    history_content += f"📄 **文件名**: [{file_name}]({file_url})  \n💯 **相似度**: {score:.2f}\n"
                    
                    st.session_state.messages.append({"role": "assistant", "content": history_content})
                    
                else:
                    # 原有的生成回答逻辑
                    system_prompt = ''
                    generate_prompt = '''
                    你是一个专业的知识库查询助手，你的任务是基于检索到的知识库内容，为用户提供准确、相关的回答。
                    请遵循以下指导原则：
                    1. 仔细分析用户的<query>和检索到的<content>之间的相关性
                    2. 如果<content>包含与<query>相关的信息：
                    - 提取关键信息并进行有条理的总结
                    - 保持原始内容的准确性，不添加未在<content>中提及的信息
                    - 使用与用户查询相同的语言回复
                    - 如有必要，可以按要点或分段组织信息，提高可读性
                    3. 如果<content>与<query>明显不相关或不包含回答问题所需的信息：
                    - 按输出语言回复："未检索到相关信息，请描述清楚问题信息，重新提交"
                    - 不要尝试猜测或编造答案
                    4. 如果<content>部分相关但不完整：
                    - 提供已有的相关信息
                    - 明确指出哪些方面的信息在知识库中缺失

                    用户查询：<query>%s</query>
                    知识库内容：<content>%s</content>
                    '''
                
                    assistant_content = ''
                    

                    # 创建一个空容器用于流式输出
                    response_placeholder = st.empty()
                    full_response = ""

                    # 使用流式生成
                    content_texts = [item['content'] for item in content_list]
                    for chunk in generate_message_stream(system_prompt, generate_prompt % (query_write, '\n'.join(content_texts)), assistant_content):
                        full_response += chunk
                        # 更新显示的内容
                        response_placeholder.markdown(full_response + "▌")
                    
                    # 收集所有引用中的图片URL
                    all_images = []
                    for ref in references:
                        if ref['images']:
                            all_images.extend(ref['images'])
                    
                    # 修复模型输出中可能不完整的图片URL
                    corrected_response = full_response
                    # 查找markdown格式的图片引用: ![alt](url)
                    img_pattern = r'!\[(.*?)\]\((.*?)\)'
                    img_matches = re.findall(img_pattern, full_response)
                    
                    # 按顺序替换图片URL
                    if len(img_matches) > 0 and len(all_images) > 0:
                        # 确保不会超出图片列表范围
                        for i, (alt_text, img_url) in enumerate(img_matches):
                            if i < len(all_images):
                                # 直接使用引用中对应位置的完整URL进行替换
                                corrected_response = corrected_response.replace(
                                    f'![{alt_text}]({img_url})', 
                                    f'![{alt_text}]({all_images[i]})'
                                )
                    
                    # 最终显示修正后的完整内容（去除光标）
                    response_placeholder.markdown(corrected_response)
                    # 更新full_response为修正后的版本
                    full_response = corrected_response

                    # 显示引用内容
                    if references:
                        st.markdown("---")
                        st.markdown("### 引用来源")
                        
                        # 显示每个引用及其相关图片
                        for ref in references:
                            with st.container():
                                # 显示文件信息
                                file_name = ref['location'].split('/')[-1]
                                file_url = ref['location']
                                score = ref['score']
                                st.markdown(f"📄 **文件名**: [{file_name}]({file_url})  \n💯 **相似度**: {score:.2f}")
                                
                                # 如果有图片，显示为缩略图
                                if ref['images']:
                                    st.write("相关图片：")
                                    
                                    # 创建多列布局，让图片并排居左展示
                                    num_images = len(ref['images'])
                                    cols_per_row = min(4, num_images)  # 每行最多4张图片
                                    cols = st.columns(cols_per_row)
                                    
                                    for i, img_url in enumerate(ref['images']):
                                        # 计算当前图片应该在哪一列
                                        col_idx = i % cols_per_row
                                        
                                        with cols[col_idx]:
                                            # 缩略图状态 - 并排居左
                                            st.image(img_url, width=150)
                                
                                # 添加分隔线
                                if ref != references[-1]:  # 如果不是最后一个引用
                                    st.markdown("---")
                    
                    # 添加到聊天历史（包含引用信息和图片）
                    history_content = f"{corrected_response}\n\n---\n### 引用来源\n"
                    for ref in references:
                        file_name = ref['location'].split('/')[-1]
                        file_url = ref['location']
                        score = ref['score']
                        history_content += f"📄 **文件名**: [{file_name}]({file_url})  \n💯 **相似度**: {score:.2f}\n"
                        if ref['images']:
                            history_content += "相关图片：\n"
                            # 创建HTML表格来并排显示图片
                            history_content += "<div style='display: flex; flex-wrap: wrap;'>\n"
                            for i, img_url in enumerate(ref['images']):
                                # 在历史记录中显示缩略图格式
                                history_content += f"<div style='margin: 5px;'><img src='{img_url}' width='150' alt='图片{i+1}'></div>\n"
                            history_content += "</div>\n"
                        if ref != references[-1]:
                            history_content += "---\n"
                    st.session_state.messages.append({"role": "assistant", "content": history_content})

if __name__ == '__main__':
    main()
