"""
Serper搜索工具
基于Serper API的Google搜索集成
"""
import asyncio
import aiohttp
import json
import os
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


async def serper_search(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    使用Serper API进行Google搜索
    
    Args:
        query: 搜索查询
        num_results: 返回结果数量
    
    Returns:
        搜索结果列表
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 SERPER_API_KEY")
    
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "q": query,
        "num": num_results
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return _parse_serper_results(data)
                else:
                    error_text = await response.text()
                    raise Exception(f"Serper API错误 {response.status}: {error_text}")
    except Exception as e:
        raise Exception(f"搜索请求失败: {e}")


def _parse_serper_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    解析Serper搜索结果
    
    Args:
        data: Serper API返回的原始数据
    
    Returns:
        格式化的搜索结果列表
    """
    results = []
    
    # 处理有机搜索结果
    if "organic" in data:
        for item in data["organic"]:
            result = {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "organic"
            }
            results.append(result)
    
    # 处理知识图谱结果
    if "knowledgeGraph" in data:
        kg = data["knowledgeGraph"]
        result = {
            "title": kg.get("title", ""),
            "url": kg.get("website", ""),
            "snippet": kg.get("description", ""),
            "source": "knowledge_graph"
        }
        results.append(result)
    
    # 处理People Also Ask结果
    if "peopleAlsoAsk" in data:
        for item in data["peopleAlsoAsk"]:
            result = {
                "title": item.get("question", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "people_also_ask"
            }
            results.append(result)
    
    return results


@tool
async def serper_search_tool(query: str, num_results: int = 10) -> str:
    """
    Serper搜索工具
    
    Args:
        query: 搜索查询
        num_results: 返回结果数量
    
    Returns:
        格式化的搜索结果
    """
    try:
        results = await serper_search(query, num_results)
        
        if not results:
            return "未找到相关搜索结果"
        
        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results[:num_results], 1):
            formatted_result = f"""
结果 {i}:
标题: {result['title']}
链接: {result['url']}
摘要: {result['snippet']}
来源: {result['source']}
"""
            formatted_results.append(formatted_result)
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"搜索失败: {str(e)}"


# 同步版本的搜索函数（用于兼容性）
def serper_search_sync(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    同步版本的Serper搜索
    
    Args:
        query: 搜索查询
        num_results: 返回结果数量
    
    Returns:
        搜索结果列表
    """
    import requests
    
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 SERPER_API_KEY")
    
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    payload = {
        "q": query,
        "num": num_results
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return _parse_serper_results(data)
        else:
            raise Exception(f"Serper API错误 {response.status_code}: {response.text}")
    except Exception as e:
        raise Exception(f"搜索请求失败: {e}")


# 测试函数
async def test_serper():
    """测试Serper搜索功能"""
    try:
        results = await serper_search("人工智能发展历史", 5)
        print("搜索结果:")
        for i, result in enumerate(results, 1):
            print(f"\n结果 {i}:")
            print(f"标题: {result['title']}")
            print(f"链接: {result['url']}")
            print(f"摘要: {result['snippet']}")
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_serper())
