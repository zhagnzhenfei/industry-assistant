"""
Open Deep Research 工具函数
基于官方文档的完整工具系统
"""
import asyncio
import logging
import os
import warnings
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import aiohttp
from .qwen_model import init_qwen_model, get_api_key_for_qwen
from .serper_search import serper_search_tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    MessageLikeRepresentation,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import (
    BaseTool,
    InjectedToolArg,
    StructuredTool,
    ToolException,
    tool,
)
from langgraph.config import get_store
try:
    from tavily import AsyncTavilyClient
except ImportError:
    AsyncTavilyClient = None

from .odr_configuration import Configuration, SearchAPI
from .odr_prompts import summarize_webpage_prompt
from .odr_state import ResearchComplete, Summary

logger = logging.getLogger(__name__)

# MCP相关导入
try:
    from langchain_mcp_adapters import MultiServerMCPClient
    from langchain_core.tools import BaseTool as LangChainBaseTool
    from langchain_mcp_adapters.tools import MCPTool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("langchain_mcp_adapters未安装，MCP工具将不可用")

# MCP服务管理器导入
try:
    from services.mcp_service_manager import MCPServiceManager
    MCP_SERVICE_MANAGER_AVAILABLE = True
except ImportError:
    MCP_SERVICE_MANAGER_AVAILABLE = False
    logger.warning("MCPServiceManager不可用，将使用HTTP客户端获取MCP工具")

# MCP工具缓存
_mcp_tools_cache = {
    "tools": [],
    "timestamp": None,
    "config_hash": None
}

def _get_config_hash(configurable: Configuration) -> str:
    """生成配置哈希值用于缓存键"""
    import hashlib
    config_str = f"{configurable.mcp_enabled}_{configurable.mcp_config}_{configurable.mcp_server_ids}"
    return hashlib.md5(config_str.encode()).hexdigest()

def _is_cache_valid(configurable: Configuration) -> bool:
    """检查MCP工具缓存是否有效"""
    if not configurable.mcp_cache_enabled:
        return False

    if not _mcp_tools_cache["timestamp"]:
        return False

    from datetime import datetime, timedelta
    cache_age = datetime.now() - _mcp_tools_cache["timestamp"]

    if cache_age > timedelta(seconds=configurable.mcp_cache_ttl):
        return False

    # 检查配置是否发生变化
    current_config_hash = _get_config_hash(configurable)
    if _mcp_tools_cache["config_hash"] != current_config_hash:
        return False

    return True

def _update_cache(tools: List[BaseTool], configurable: Configuration):
    """更新MCP工具缓存"""
    if configurable.mcp_cache_enabled:
        from datetime import datetime
        _mcp_tools_cache.update({
            "tools": tools,
            "timestamp": datetime.now(),
            "config_hash": _get_config_hash(configurable)
        })
        logger.info(f"MCP工具缓存已更新，缓存了 {len(tools)} 个工具")

def _clear_cache():
    """清除MCP工具缓存"""
    global _mcp_tools_cache
    _mcp_tools_cache = {
        "tools": [],
        "timestamp": None,
        "config_hash": None
    }
    logger.info("MCP工具缓存已清除")

def get_mcp_cache_info() -> dict:
    """获取MCP工具缓存信息"""
    if not _mcp_tools_cache["timestamp"]:
        return {
            "has_cache": False,
            "tools_count": 0,
            "cache_age": None
        }

    from datetime import datetime
    cache_age = datetime.now() - _mcp_tools_cache["timestamp"]

    return {
        "has_cache": True,
        "tools_count": len(_mcp_tools_cache["tools"]),
        "cache_age_seconds": int(cache_age.total_seconds()),
        "config_hash": _mcp_tools_cache["config_hash"]
    }

def reload_mcp_tools(config: RunnableConfig) -> None:
    """强制重新加载MCP工具（清除缓存）"""
    configurable = Configuration.from_runnable_config(config)
    _clear_cache()
    logger.info("MCP工具缓存已清除，下次调用将重新从服务器加载")

##########################
# Tavily 搜索工具工具
##########################
TAVILY_SEARCH_DESCRIPTION = (
    "专为全面、准确和可信结果优化的搜索引擎。"
    "当您需要回答有关当前事件的问题时很有用。"
)

@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: RunnableConfig = None
) -> str:
    """从Tavily搜索API获取并总结搜索结果。

    Args:
        queries: 要执行的搜索查询列表
        max_results: 每个查询返回的最大结果数
        topic: 搜索结果的主题过滤器（general、news或finance）
        config: API密钥和模型设置的运行时配置

    Returns:
        包含总结搜索结果的格式化字符串
    """
    # 步骤1：异步执行搜索查询
    search_results = await tavily_search_async(
        queries,
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
        config=config
    )
    
    # 步骤2：按URL去重结果，避免多次处理相同内容
    unique_results = {}
    for response in search_results:
        for result in response['results']:
            url = result['url']
            if url not in unique_results:
                unique_results[url] = {**result, "query": response['query']}
    
    # 步骤3：设置摘要模型和配置
    configurable = Configuration.from_runnable_config(config)
    
    # 字符限制以保持在模型token限制内（可配置）
    max_char_to_include = configurable.max_content_length
    
    # 初始化摘要模型和重试逻辑
    summarization_model = init_qwen_model(
        model=configurable.summarization_model,
        max_tokens=configurable.summarization_model_max_tokens
    )
    
    # 步骤4：创建摘要任务（跳过空内容）
    async def noop():
        """无操作函数，用于没有原始内容的结果"""
        return None
    
    summarization_tasks = [
        summarize_webpage_content(result, summarization_model, max_char_to_include)
        if result.get('raw_content') else noop()
        for result in unique_results.values()
    ]
    
    # 步骤5：并行执行摘要任务
    summaries = await asyncio.gather(*summarization_tasks, return_exceptions=True)
    
    # 步骤6：格式化最终结果
    formatted_results = []
    for i, (url, result) in enumerate(unique_results.items()):
        summary = summaries[i]
        if isinstance(summary, Exception):
            logger.warning(f"摘要失败 {url}: {summary}")
            formatted_results.append(f"**来源**: {result['title']}\n**URL**: {url}\n**内容**: {result.get('content', '无内容')}")
        elif summary:
            formatted_results.append(f"**来源**: {result['title']}\n**URL**: {url}\n**摘要**: {summary.summary}\n**关键摘录**: {summary.key_excerpts}")
        else:
            formatted_results.append(f"**来源**: {result['title']}\n**URL**: {url}\n**内容**: {result.get('content', '无内容')}")
    
    return "\n\n".join(formatted_results)


async def summarize_webpage_content(result: Dict[str, Any], model: BaseChatModel, max_char_to_include: int) -> Optional[Summary]:
    """总结网页内容"""
    try:
        raw_content = result.get('raw_content', '')
        if not raw_content:
            return None
        
        # 截断内容以保持在token限制内
        if len(raw_content) > max_char_to_include:
            raw_content = raw_content[:max_char_to_include] + "..."
        
        prompt = summarize_webpage_prompt.format(
            webpage_content=raw_content,
            date=get_today_str()
        )
        
        response = await model.ainvoke([HumanMessage(content=prompt)])
        return response
        
    except Exception as e:
        logger.error(f"摘要网页内容失败: {e}")
        return None


async def tavily_search_async(
    queries: List[str],
    max_results: int = 5,
    topic: str = "general",
    include_raw_content: bool = True,
    config: RunnableConfig = None
) -> List[Dict[str, Any]]:
    """异步执行Tavily搜索"""
    configurable = Configuration.from_runnable_config(config)
    
    # 获取Tavily API密钥
    tavily_api_key = get_api_key_for_model("tavily", config)
    if not tavily_api_key:
        raise ValueError("未找到Tavily API密钥")
    
    client = AsyncTavilyClient(api_key=tavily_api_key)
    
    # 并行执行搜索查询
    search_tasks = [
        client.search(
            query=query,
            max_results=max_results,
            topic=topic,
            include_raw_content=include_raw_content
        )
        for query in queries
    ]
    
    results = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    # 处理结果
    valid_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"搜索查询失败 '{queries[i]}': {result}")
            valid_results.append({
                'query': queries[i],
                'results': [],
                'error': str(result)
            })
        else:
            valid_results.append({
                'query': queries[i],
                'results': result.get('results', [])
            })
    
    return valid_results


##########################
# 工具函数
##########################



def get_today_str() -> str:
    """获取今天的日期字符串"""
    return datetime.now().strftime("%Y-%m-%d")


def get_api_key_for_model(model_name: str, config: RunnableConfig = None) -> Optional[str]:
    """获取模型的API密钥"""
    if not config:
        return None
    
    configurable = config.get("configurable", {})
    
    # 检查配置中的API密钥
    if model_name in configurable:
        return configurable[model_name]
    
    # 检查环境变量
    env_key = f"{model_name.upper()}_API_KEY"
    return os.getenv(env_key)


def get_model_token_limit(model_name: str) -> Optional[int]:
    """获取模型的token限制"""
    model_limits = {
        "qwen-plus": 30000,
        "qwen-max": 30000,
        "qwen-turbo": 30000,
        "openai:gpt-4o": 128000,
        "openai:gpt-4o-mini": 128000,
        "openai:gpt-4o-nano": 128000,
        "anthropic:claude-3-5-sonnet": 200000,
        "anthropic:claude-3-5-haiku": 200000,
    }
    
    return model_limits.get(model_name)


def is_token_limit_exceeded(error: Exception, model_name: str) -> bool:
    """检查错误是否是token限制超出"""
    error_str = str(error).lower()
    token_limit_indicators = [
        "token limit",
        "context length",
        "maximum context",
        "too many tokens",
        "token count",
        "context window"
    ]
    
    return any(indicator in error_str for indicator in token_limit_indicators)


def get_notes_from_tool_calls(messages: List[MessageLikeRepresentation]) -> List[str]:
    """从工具调用中提取笔记"""
    notes = []
    for message in messages:
        if hasattr(message, 'content') and message.content:
            if isinstance(message.content, str):
                notes.append(message.content)
            elif isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict) and 'text' in item:
                        notes.append(item['text'])
    return notes


def remove_up_to_last_ai_message(messages: List[MessageLikeRepresentation]) -> List[MessageLikeRepresentation]:
    """移除到最后一个AI消息之前的所有消息"""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            return messages[i:]
    return messages


async def get_mcp_tools(config: RunnableConfig) -> List[BaseTool]:
    """从MCP服务器获取工具列表（带缓存）"""
    if not MCP_AVAILABLE:
        logger.warning("MCP适配器不可用，跳过MCP工具加载")
        return []

    configurable = Configuration.from_runnable_config(config)

    # 检查是否启用MCP工具
    if not configurable.mcp_enabled:
        logger.info("MCP工具已禁用")
        return []

    # 检查是否有MCP配置
    if not configurable.mcp_config:
        logger.warning("未配置MCP服务器，跳过MCP工具加载")
        return []

    # 检查缓存
    if _is_cache_valid(configurable):
        logger.info("使用缓存的MCP工具")
        return _mcp_tools_cache["tools"]

    mcp_tools = []

    try:
        # 构建服务器配置
        server_config = {}

        if configurable.mcp_config.url:
            # HTTP/SSE传输
            if configurable.mcp_config.transport in ["http", "sse"]:
                server_config = {
                    "mcpServers": {
                        "default": {
                            "url": configurable.mcp_config.url,
                            "transport": configurable.mcp_config.transport
                        }
                    }
                }
            elif configurable.mcp_config.transport == "websocket":
                server_config = {
                    "mcpServers": {
                        "default": {
                            "url": configurable.mcp_config.url,
                            "transport": "websocket"
                        }
                    }
                }

        elif configurable.mcp_config.command:
            # STDIO传输
            server_config = {
                "mcpServers": {
                    "default": {
                        "command": configurable.mcp_config.command,
                        "args": configurable.mcp_config.args or [],
                        "env": configurable.mcp_config.env or {}
                    }
                }
            }

        if not server_config:
            logger.warning("无法构建MCP服务器配置")
            return []

        # 创建MCP客户端
        client = MultiServerMCPClient(server_config)

        # 获取工具
        mcp_tools = await client.get_tools()

        logger.info(f"成功从MCP服务器加载 {len(mcp_tools)} 个工具")

        # 关闭客户端连接
        if hasattr(client, 'close'):
            await client.close()
        elif hasattr(client, '__aexit__'):
            await client.__aexit__(None, None, None)

        # 更新缓存
        _update_cache(mcp_tools, configurable)

    except Exception as e:
        logger.error(f"获取MCP工具失败: {e}")
        # 如果有可用缓存，返回缓存作为降级策略
        if _mcp_tools_cache["tools"]:
            logger.warning("MCP服务器连接失败，使用缓存工具作为降级策略")
            return _mcp_tools_cache["tools"]
        return []

    return mcp_tools


async def get_tools_by_role(role: str, config: RunnableConfig) -> List[BaseTool]:
    """根据角色获取相应的工具列表

    Args:
        role: 角色 ('supervisor', 'researcher', 'writer', 'reviewer')
        config: 运行时配置

    Returns:
        适合该角色的工具列表
    """
    all_tools = await get_all_tools(config)

    if not all_tools:
        return []

    # 定义角色工具映射
    role_tool_mapping = {
        "supervisor": {
            "required": [],
            "excluded": ["tavily_search", "serper_search", "serper_search_tool", "tavily_search_search"],
            "mcp_categories": ["management", "coordination", "monitoring"]
        },
        "researcher": {
            "required": [],
            "excluded": [],
            "mcp_categories": ["search", "analysis", "data_collection", "research"]
        },
        "writer": {
            "required": [],
            "excluded": ["tavily_search", "serper_search", "serper_search_tool", "tavily_search_search"],
            "mcp_categories": ["writing", "formatting", "translation", "summarization"]
        },
        "reviewer": {
            "required": [],
            "excluded": ["tavily_search", "serper_search", "serper_search_tool", "tavily_search_search"],
            "mcp_categories": ["analysis", "validation", "quality_check"]
        }
    }

    if role not in role_tool_mapping:
        logger.warning(f"未知角色: {role}，返回所有工具")
        return all_tools

    role_config = role_tool_mapping[role]
    filtered_tools = []

    for tool in all_tools:
        tool_name = tool.name if hasattr(tool, 'name') else str(tool)

        # 检查是否在排除列表中
        if tool_name in role_config["excluded"]:
            continue

        # 检查是否为MCP工具并验证类别
        if hasattr(tool, '_mcp_tool') and hasattr(tool, 'metadata'):
            tool_categories = tool.metadata.get('categories', [])
            allowed_categories = role_config["mcp_categories"]

            # 如果设置了允许的类别且工具类别不在其中，则跳过
            if allowed_categories and not any(cat in tool_categories for cat in allowed_categories):
                continue

        filtered_tools.append(tool)

    # 确保必需工具存在
    required_tool_names = role_config["required"]
    for required_name in required_tool_names:
        if not any(tool.name == required_name for tool in filtered_tools):
            # 如果必需工具不存在，从all_tools中查找并添加
            for tool in all_tools:
                if hasattr(tool, 'name') and tool.name == required_name:
                    filtered_tools.append(tool)
                    break

    logger.info(f"为角色 {role} 筛选出 {len(filtered_tools)} 个工具")
    return filtered_tools


async def get_tools_for_researcher(config: RunnableConfig) -> List[BaseTool]:
    """为研究者节点获取工具集合"""
    return await get_tools_by_role("researcher", config)


async def get_all_tools(config: RunnableConfig) -> List[BaseTool]:
    """获取所有可用工具"""
    tools = []

    # 添加搜索工具
    configurable = Configuration.from_runnable_config(config)
    if configurable.search_api == SearchAPI.TAVILY:
        tools.append(tavily_search)
    elif configurable.search_api == SearchAPI.SERPER:
        tools.append(serper_search_tool)

    # 添加Text2SQL工具
    try:
        text2sql_enabled = getattr(configurable, 'text2sql_enabled', True)
        if text2sql_enabled:
            from .text2sql_tool import query_database
            tools.append(query_database)
            logger.info("Text2SQL工具已添加")
    except Exception as e:
        logger.error(f"加载Text2SQL工具失败: {e}", exc_info=True)

    # 添加MCP工具
    try:
        mcp_tools = await get_mcp_tools(config)
        tools.extend(mcp_tools)
    except Exception as e:
        logger.error(f"加载MCP工具失败: {e}")

    return tools


def openai_websearch_called(message: MessageLikeRepresentation) -> bool:
    """检查是否调用了OpenAI原生网络搜索"""
    if not hasattr(message, 'tool_calls'):
        return False
    
    for tool_call in message.tool_calls:
        if tool_call.get('name') == 'web_search':
            return True
    
    return False


def anthropic_websearch_called(message: MessageLikeRepresentation) -> bool:
    """检查是否调用了Anthropic原生网络搜索"""
    if not hasattr(message, 'tool_calls'):
        return False
    
    for tool_call in message.tool_calls:
        if tool_call.get('name') == 'web_search':
            return True
    
    return False
