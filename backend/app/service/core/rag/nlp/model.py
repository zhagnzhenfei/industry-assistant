from openai import OpenAI
from llama_index.core.data_structs import Node
from llama_index.core.schema import NodeWithScore
from llama_index.postprocessor.dashscope_rerank import DashScopeRerank
import numpy as np

import os
from dotenv import load_dotenv
load_dotenv()


def rerank_similarity(query, texts):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    # 创建节点列表
    nodes = [NodeWithScore(node=Node(text=text), score=1.0) for text in texts]

    # 初始化 DashScopeRerank
    dashscope_rerank = DashScopeRerank(top_n=len(texts), api_key=api_key)

    # 执行重排序
    results = dashscope_rerank.postprocess_nodes(nodes, query_str=query)

    # 提取分数
    scores = [res.score for res in results]
    scores = np.array(scores)

    # 返回分数和一个占位符
    return scores, None




def generate_embedding(text: str, api_key: str = None, base_url: str = None, model_name: str = None, dimensions: int = 1024, encoding_format: str = "float"):

    if model_name is None:
        model_name = "text-embedding-v4"

    api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
    base_url = base_url or os.getenv("DASHSCOPE_BASE_URL")

    # 检查API密钥是否配置
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY未配置，无法生成嵌入向量")

    # 使用 requests 直接调用 SiliconFlow API
    import requests

    url = f"{base_url}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model_name,
        "input": text
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        embedding = result["data"][0]["embedding"]
        print(f"✅ 成功使用 {model_name} 生成{len(embedding)}维嵌入向量")
        return embedding

    except Exception as e:
        print(f"❌ 嵌入向量生成失败: {e}")
        raise e
