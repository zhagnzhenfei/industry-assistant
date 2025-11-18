"""
Open Deep Research 研究者子图
基于官方文档的完整研究者实现
"""
import asyncio
from typing import Literal
from .qwen_model import init_qwen_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .odr_configuration import Configuration
from .odr_prompts import (
    compress_research_simple_human_message,
    compress_research_system_prompt,
    research_system_prompt,
)
from .odr_state import (
    ResearcherOutputState,
    ResearcherState,
)
from .odr_utils import (
    anthropic_websearch_called,
    get_all_tools,
    get_tools_for_researcher,
    get_api_key_for_model,
    get_today_str,
    is_token_limit_exceeded,
    openai_websearch_called,
    remove_up_to_last_ai_message,
)

# 初始化可配置模型，我们将在整个智能体中使用
# 模型名称从环境变量读取
import logging
logger = logging.getLogger(__name__)

configurable_model = init_qwen_model(
    model=None,  # 从环境变量LLM_MODEL读取
    max_tokens=4000
)

logger.info(f"🤖 研究者模型初始化: model={configurable_model.model_name}")


async def researcher(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher_tools"]]:
    """个体研究者，对特定主题进行专注研究。
    
    此研究者被监督者给予特定研究主题，并使用可用工具（搜索、MCP工具）
    收集全面信息。
    
    Args:
        state: 当前研究者状态，包含消息和主题上下文
        config: 运行时配置，包含模型设置和工具可用性
        
    Returns:
        命令，指示继续到researcher_tools进行工具执行
    """
    # 步骤1：加载配置并验证工具可用性
    configurable = Configuration.from_runnable_config(config)
    researcher_messages = state.get("researcher_messages", [])
    
    # 添加日志监控
    import logging
    logger = logging.getLogger(__name__)
    current_iteration = state.get("tool_call_iterations", 0) + 1
    current_searches = state.get("total_searches", 0)
    logger.info(
        f"[RESEARCHER] 📊 第{current_iteration}轮 | "
        f"已搜索{current_searches}次 | "
        f"限制:{configurable.max_react_tool_calls}轮/{configurable.max_total_searches_per_researcher}次搜索"
    )
    
    # 获取研究者专用的工具集合（搜索、MCP工具）
    tools = await get_tools_for_researcher(config)
    
    # 添加详细的工具列表日志
    logger.info(f"[RESEARCHER] 🔧 可用工具数量: {len(tools)}")
    for i, tool in enumerate(tools, 1):
        tool_name = tool.name if hasattr(tool, 'name') else str(tool)
        tool_desc = tool.description[:50] if hasattr(tool, 'description') else "无描述"
        logger.info(f"[RESEARCHER] 🔧 工具{i}: {tool_name} - {tool_desc}...")
    
    if len(tools) == 0:
        raise ValueError(
            "未找到进行研究所需的工具：请在配置中配置搜索API或添加MCP工具。"
        )
    
    # 步骤2：配置研究者模型和工具
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # 准备系统提示，如果可用则包含MCP上下文
    researcher_prompt = research_system_prompt.format(
        mcp_prompt=configurable.mcp_prompt or "", 
        date=get_today_str()
    )
    
    # 配置模型，绑定工具，重试逻辑和设置
    research_model = (
        configurable_model
        .bind_tools(tools)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(research_model_config)
    )
    
    # 步骤3：使用系统上下文生成研究者响应
    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages
    response = await research_model.ainvoke(messages)
    
    # 步骤4：从ChatResult中提取AIMessage
    ai_message = response.generations[0].message
    
    # 步骤5：更新状态并继续到工具执行
    return Command(
        goto="researcher_tools",
        update={
            "researcher_messages": [ai_message],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
        }
    )


# 工具执行辅助函数
async def execute_tool_safely(tool, args, config):
    """安全执行工具，包含错误处理和超时设置"""
    try:
        # 添加30秒超时
        return await asyncio.wait_for(tool.ainvoke(args, config), timeout=30.0)
    except asyncio.TimeoutError:
        return f"工具执行超时: {tool.name if hasattr(tool, 'name') else 'unknown'}"
    except Exception as e:
        return f"执行工具错误: {str(e)}"


async def researcher_tools(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher", "compress_research"]]:
    """执行研究者调用的工具，包括搜索工具。
    
    此函数处理各种类型的研究者工具调用：
    1. 搜索工具（serper_search、tavily_search、web_search）- 信息收集
    2. MCP工具 - 外部工具集成
    3. ResearchComplete - 表示个体研究任务完成
    
    Args:
        state: 当前研究者状态，包含消息和迭代计数
        config: 运行时配置，包含研究限制和工具设置
        
    Returns:
        命令，指示继续研究循环或继续到压缩
    """
    # 步骤1：提取当前状态并检查早期退出条件
    configurable = Configuration.from_runnable_config(config)
    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = researcher_messages[-1]
    
    # 早期退出如果没有进行工具调用（包括原生网络搜索）
    has_tool_calls = bool(most_recent_message.tool_calls)
    has_native_search = (
        openai_websearch_called(most_recent_message) or 
        anthropic_websearch_called(most_recent_message)
    )
    
    if not has_tool_calls and not has_native_search:
        return Command(goto="compress_research")
    
    # 步骤2：处理其他工具调用（搜索、MCP工具等）
    tools = await get_tools_for_researcher(config)
    tools_by_name = {
        tool.name if hasattr(tool, "name") else tool.get("name", "web_search"): tool 
        for tool in tools
    }
    
    # 获取工具调用并限制并行搜索数量
    tool_calls = most_recent_message.tool_calls
    
    # 统计搜索工具调用
    search_tool_calls = [
        tc for tc in tool_calls 
        if any(keyword in tc["name"].lower() for keyword in ["search", "tavily", "serper"])
    ]
    other_tool_calls = [tc for tc in tool_calls if tc not in search_tool_calls]
    
    # 限制每轮并行搜索数量
    max_searches_per_iter = configurable.max_searches_per_iteration
    if len(search_tool_calls) > max_searches_per_iter:
        # 只保留前N个搜索工具调用
        search_tool_calls = search_tool_calls[:max_searches_per_iter]
        # 添加警告消息
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"[RESEARCHER] ⚠️ 限制并行搜索：原计划{len(tool_calls)}个搜索，"
            f"限制为{max_searches_per_iter}个"
        )
    
    # 合并回所有工具调用
    tool_calls = search_tool_calls + other_tool_calls
    
    # 检查总搜索次数限制
    total_searches = state.get("total_searches", 0) + len(search_tool_calls)
    max_total = configurable.max_total_searches_per_researcher
    
    if total_searches > max_total:
        # 超过总搜索限制，立即结束研究
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"[RESEARCHER] ⛔ 达到搜索次数限制：{total_searches}/{max_total}，结束研究"
        )
        # 创建截断消息
        truncated_msg = ToolMessage(
            content=f"已达到最大搜索次数限制({max_total})，研究结束。",
            name="system",
            tool_call_id="truncate_id"
        )
        return Command(
            goto="compress_research",
            update={
                "researcher_messages": [truncated_msg],
                "total_searches": total_searches
            }
        )
    
    # 并行执行所有工具调用
    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config) 
        for tool_call in tool_calls
    ]
    # 添加60秒总超时，防止整个工具执行过程卡住
    try:
        observations = await asyncio.wait_for(
            asyncio.gather(*tool_execution_tasks, return_exceptions=True), 
            timeout=60.0
        )
    except asyncio.TimeoutError:
        observations = ["工具执行总超时"] * len(tool_calls)
    
    # 从执行结果创建工具消息
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) 
        for observation, tool_call in zip(observations, tool_calls)
    ]
    
    # 步骤3：检查晚期退出条件（处理工具后）
    exceeded_iterations = state.get("tool_call_iterations", 0) >= configurable.max_react_tool_calls
    research_complete_called = any(
        tool_call["name"] == "ResearchComplete" 
        for tool_call in most_recent_message.tool_calls
    )
    
    if exceeded_iterations or research_complete_called:
        # 结束研究并继续到压缩
        return Command(
            goto="compress_research",
            update={
                "researcher_messages": tool_outputs,
                "total_searches": total_searches  # 更新总搜索次数
            }
        )
    
    # 继续研究循环，包含工具结果
    return Command(
        goto="researcher",
        update={
            "researcher_messages": tool_outputs,
            "total_searches": total_searches  # 更新总搜索次数
        }
    )


async def compress_research(state: ResearcherState, config: RunnableConfig):
    """压缩并综合研究发现为简洁、结构化的摘要。
    
    此函数获取研究者的所有研究发现、工具输出和AI消息，
    并将它们提炼为干净、全面的摘要，同时保留所有重要信息和发现。
    
    Args:
        state: 当前研究者状态，包含累积的研究消息
        config: 运行时配置，包含压缩模型设置
        
    Returns:
        包含压缩研究摘要和原始笔记的字典
    """
    # 步骤1：配置压缩模型
    configurable = Configuration.from_runnable_config(config)
    synthesizer_model = configurable_model.with_config({
        "model": configurable.compression_model,
        "max_tokens": configurable.compression_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.compression_model, config),
        "tags": ["langsmith:nostream"]
    })
    
    # 步骤2：准备压缩消息
    researcher_messages = state.get("researcher_messages", [])
    
    # 添加指令，从研究模式切换到压缩模式
    researcher_messages.append(HumanMessage(content=compress_research_simple_human_message))
    
    # 步骤3：尝试压缩，包含token限制问题的重试逻辑
    synthesis_attempts = 0
    max_attempts = 3
    
    while synthesis_attempts < max_attempts:
        try:
            # 创建专注于压缩任务的系统提示
            compression_prompt = compress_research_system_prompt.format(date=get_today_str())
            messages = [SystemMessage(content=compression_prompt)] + researcher_messages
            
            # 执行压缩
            response = await synthesizer_model.ainvoke(messages)
            
            # 从所有工具和AI消息中提取原始笔记
            raw_notes_content = "\n".join([
                str(message.content) 
                for message in filter_messages(researcher_messages, include_types=["tool", "ai"])
            ])
            
            # 返回成功的压缩结果
            return {
                "compressed_research": str(response.content),
                "raw_notes": [raw_notes_content]
            }
            
        except Exception as e:
            synthesis_attempts += 1
            
            # 通过移除旧消息处理token限制超出
            if is_token_limit_exceeded(e, configurable.research_model):
                researcher_messages = remove_up_to_last_ai_message(researcher_messages)
                continue
            
            # 对于其他错误，继续重试
            continue
    
    # 步骤4：如果所有尝试都失败，返回错误结果
    raw_notes_content = "\n".join([
        str(message.content) 
        for message in filter_messages(researcher_messages, include_types=["tool", "ai"])
    ])
    
    return {
        "compressed_research": "错误合成研究报告：超过最大重试次数",
        "raw_notes": [raw_notes_content]
    }


# 研究者子图构建
# 创建个体研究者工作流，用于对特定主题进行专注研究
researcher_builder = StateGraph(
    ResearcherState, 
    output=ResearcherOutputState, 
    config_schema=Configuration
)

# 添加研究执行和压缩的研究者节点
researcher_builder.add_node("researcher", researcher)                 # 主研究者逻辑
researcher_builder.add_node("researcher_tools", researcher_tools)     # 工具执行处理器
researcher_builder.add_node("compress_research", compress_research)   # 研究压缩

# 定义研究者工作流边
researcher_builder.add_edge(START, "researcher")           # 研究者入口点
researcher_builder.add_edge("compress_research", END)      # 压缩后退出点

# 编译研究者子图以供监督者并行执行
researcher_subgraph = researcher_builder.compile()
