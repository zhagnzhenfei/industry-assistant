"""
Open Deep Research 主工作流图
基于官方文档的完整主工作流实现
"""
import asyncio
import logging
from typing import Literal
# 临时解决方案：使用OpenAI直接调用
import openai

logger = logging.getLogger(__name__)
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

# 导入聊天模型初始化函数
from .qwen_model import init_qwen_model

from .odr_configuration import Configuration
from .odr_prompts import (
    clarify_with_user_instructions,
    final_report_generation_prompt,
    lead_researcher_prompt,
    transform_messages_into_research_topic_prompt,
)
from .odr_state import (
    AgentInputState,
    AgentState,
    ClarifyWithUser,
    ResearchQuestion,
)
from .odr_utils import (
    get_api_key_for_model,
    get_model_token_limit,
    get_today_str,
    is_token_limit_exceeded,
)

# 导入子图
from .odr_supervisor import supervisor_subgraph

# 初始化可配置模型，我们将在整个智能体中使用
# 模型名称从环境变量读取（LLM_MODEL或默认qwen-plus）
import logging
logger = logging.getLogger(__name__)

configurable_model = init_qwen_model(
    model=None,  # 从环境变量LLM_MODEL读取
    max_tokens=4000
)

logger.info(f"🤖 全局模型初始化完成: model={configurable_model.model_name}")


async def clarify_with_user(state: AgentState, config: RunnableConfig) -> Command[Literal["write_research_brief", "__end__"]]:
    """分析用户消息，如果研究范围不清楚则询问澄清问题。
    
    此函数确定用户的请求在继续研究之前是否需要澄清。
    如果澄清被禁用或不需要，它直接继续研究。
    
    Args:
        state: 当前智能体状态，包含用户消息
        config: 运行时配置，包含模型设置和偏好
        
    Returns:
        命令，指示以澄清问题结束或继续到研究简报
    """
    logger.info("=== 用户澄清阶段开始 ===")
    
    try:
        # 步骤1：检查配置中是否启用了澄清
        configurable = Configuration.from_runnable_config(config)
        logger.info(f"配置加载成功，允许澄清: {configurable.allow_clarification}")
        
        if not configurable.allow_clarification:
            # 跳过澄清步骤，直接继续研究
            logger.info("澄清被禁用，直接进入研究规划阶段")
            return Command(goto="write_research_brief")
        
        # 步骤2：为结构化澄清分析准备模型
        messages = state["messages"]
        logger.info(f"用户消息数量: {len(messages)}")
        
        model_config = {
            "model": configurable.research_model,
            "max_tokens": configurable.research_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.research_model, config),
            "tags": ["langsmith:nostream"]
        }
        logger.info(f"模型配置: {model_config}")
        
        # 配置模型，包含结构化输出和重试逻辑
        logger.info("配置澄清模型...")
        clarification_model = (
            configurable_model
            .with_structured_output(ClarifyWithUser)
            .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
            .with_config(model_config)
        )
        logger.info("澄清模型配置完成")
        
        # 步骤3：分析是否需要澄清
        prompt_content = clarify_with_user_instructions.format(
            messages=get_buffer_string(messages), 
            date=get_today_str()
        )
        logger.info(f"澄清提示构建完成，长度: {len(prompt_content)}")
        
        logger.info("调用模型进行澄清分析...")
        response = await clarification_model.ainvoke([HumanMessage(content=prompt_content)])
        logger.info(f"澄清分析结果: {response}")
        
        # 步骤4：基于澄清分析进行路由
        if response.need_clarification:
            # 以澄清问题结束，供用户回答
            logger.info("需要澄清，返回澄清问题")
            return Command(
                goto=END, 
                update={"messages": [AIMessage(content=response.question)]}
            )
        else:
            # 继续研究，包含验证消息
            logger.info("无需澄清，进入研究规划阶段")
            return Command(
                goto="write_research_brief", 
                update={"messages": [AIMessage(content=response.verification)]}
            )
            
    except Exception as e:
        logger.error(f"澄清阶段出错: {e}")
        import traceback
        traceback.print_exc()
        # 出错时直接进入研究规划阶段
        logger.info("出错时直接进入研究规划阶段")
        return Command(goto="write_research_brief")


async def write_research_brief(state: AgentState, config: RunnableConfig) -> Command[Literal["research_supervisor"]]:
    """将用户消息转换为结构化研究简报并初始化监督者。
    
    此函数分析用户的消息并生成将指导研究监督者的专注研究简报。
    它还使用适当的提示和说明设置初始监督者上下文。
    
    Args:
        state: 当前智能体状态，包含用户消息
        config: 运行时配置，包含模型设置
        
    Returns:
        命令，指示继续到研究监督者，包含初始化的上下文
    """
    # 步骤1：为结构化输出设置研究模型
    configurable = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # 配置模型，用于结构化研究问题生成
    research_model = (
        configurable_model
        .with_structured_output(ResearchQuestion)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(research_model_config)
    )
    
    # 步骤2：从用户消息生成结构化研究简报
    prompt_content = transform_messages_into_research_topic_prompt.format(
        messages=get_buffer_string(state.get("messages", [])),
        date=get_today_str()
    )
    response = await research_model.ainvoke([HumanMessage(content=prompt_content)])
    
    # 步骤3：使用研究简报和说明初始化监督者（基础版本，进度信息将在supervisor节点中动态更新）
    # 计算阶段边界，用于提示词中的数学表达式
    early_stage_end = configurable.max_researcher_iterations // 3
    middle_stage_start = early_stage_end + 1
    middle_stage_end = 2 * configurable.max_researcher_iterations // 3
    final_stage_start = middle_stage_end + 1

    supervisor_system_prompt = lead_researcher_prompt.format(
        date=get_today_str(),
        max_researcher_iterations=configurable.max_researcher_iterations,
        max_concurrent_research_units=configurable.max_concurrent_research_units,
        current_iteration=1,
        used_research_units=0,
        remaining_iterations=configurable.max_researcher_iterations,
        remaining_units=configurable.max_concurrent_research_units,
        # 提供计算好的阶段边界值，避免在format中使用数学表达式
        early_stage_end=early_stage_end,
        middle_stage_start=middle_stage_start,
        middle_stage_end=middle_stage_end,
        final_stage_start=final_stage_start,
        mcp_prompt=""
    )
    
    return Command(
        goto="research_supervisor",
        update={
            "research_brief": response.research_brief,
            "supervisor_messages": {
                "type": "override",
                "value": [
                    SystemMessage(content=supervisor_system_prompt),
                    HumanMessage(content=response.research_brief)
                ]
            },
            # 初始化计数器
            "research_iterations": 0,
            "used_research_units": 0
        }
    )


async def final_report_generation(state: AgentState, config: RunnableConfig):
    """使用token限制重试逻辑生成最终综合研究报告。
    
    此函数获取所有收集的研究发现，并使用配置的报告生成模型
    将它们综合为结构良好、全面的最终报告。
    
    Args:
        state: 智能体状态，包含研究发现和上下文
        config: 运行时配置，包含模型设置和API密钥
        
    Returns:
        包含最终报告和清理状态的字典
    """
    # 步骤1：提取研究发现并准备状态清理
    notes = state.get("notes", [])
    cleared_state = {"notes": {"type": "override", "value": []}}
    findings = "\n".join(notes)
    
    # 步骤2：配置最终报告生成模型
    configurable = Configuration.from_runnable_config(config)
    writer_model_config = {
        "model": configurable.final_report_model,
        "max_tokens": configurable.final_report_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.final_report_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # 步骤3：尝试报告生成，包含token限制重试逻辑
    max_retries = 3
    current_retry = 0
    findings_token_limit = None
    
    while current_retry <= max_retries:
        try:
            # 创建包含所有研究上下文的综合提示
            final_report_prompt = final_report_generation_prompt.format(
                research_brief=state.get("research_brief", ""),
                messages=get_buffer_string(state.get("messages", [])),
                findings=findings,
                date=get_today_str()
            )
            
            # 生成最终报告
            final_report = await configurable_model.with_config(writer_model_config).ainvoke([
                HumanMessage(content=final_report_prompt)
            ])
            
            base_report = final_report.content
            
            # 尝试添加可视化增强
            try:
                from services.visualization.report_enhancer import ReportEnhancer
                from configs.visualization_config import get_visualization_settings
                
                logger.info("[REPORT] 🎨 开始可视化增强...")
                settings = get_visualization_settings()
                enhancer = ReportEnhancer(
                    configurable_model.with_config(writer_model_config),
                    base_url=settings.base_url
                )
                
                result = await enhancer.enhance(base_report)
                enhanced_report = result["enhanced_report"]
                
                logger.info(f"[REPORT] ✓ 可视化完成: {result['chart_count']}个图表, 耗时{result['processing_time']:.2f}秒")
                
                # 使用增强后的报告
                final_report_content = enhanced_report
            except Exception as e:
                logger.warning(f"[REPORT] ⚠️ 可视化失败: {e}")
                # 降级：使用基础报告
                final_report_content = base_report
            
            # 返回成功的报告生成
            return {
                "final_report": final_report_content, 
                "messages": [final_report],
                **cleared_state
            }
            
        except Exception as e:
            # 通过渐进截断处理token限制超出错误
            if is_token_limit_exceeded(e, configurable.final_report_model):
                current_retry += 1
                
                if current_retry == 1:
                    # 第一次重试：确定初始截断限制
                    model_token_limit = get_model_token_limit(configurable.final_report_model)
                    if not model_token_limit:
                        return {
                            "final_report": f"生成最终报告错误：Token限制超出，但是，我们无法确定模型的最大上下文长度。请在deep_researcher/utils.py中更新模型映射，包含此信息。{e}",
                            "messages": [AIMessage(content="由于token限制，报告生成失败")],
                            **cleared_state
                        }
                    # 使用4x token限制作为截断的字符近似
                    findings_token_limit = model_token_limit * 4
                else:
                    # 后续重试：每次减少10%
                    findings_token_limit = int(findings_token_limit * 0.9)
                
                # 截断发现并重试
                findings = findings[:findings_token_limit]
                continue
            else:
                # 非token限制错误：立即返回错误
                return {
                    "final_report": f"生成最终报告错误: {e}",
                    "messages": [AIMessage(content="由于错误，报告生成失败")],
                    **cleared_state
                }
    
    # 步骤4：如果所有重试都耗尽，返回失败结果
    return {
        "final_report": "生成最终报告错误：超过最大重试次数",
        "messages": [AIMessage(content="在最大重试次数后报告生成失败")],
        **cleared_state
    }




# ═══════════════════════════════════════════════════════════════
# 主深度研究者图构建（支持可选记忆功能）
# ═══════════════════════════════════════════════════════════════

def build_deep_researcher_graph():
    """构建深度研究者图（简化版，无记忆功能）

    Returns:
        编译后的图
    """
    logger.info("🏗️ 构建深度研究者图（标准流程）")

    # 创建图构建器
    builder = StateGraph(
        AgentState,
        input=AgentInputState,
        config_schema=Configuration
    )

    # 添加核心节点
    builder.add_node("clarify_with_user", clarify_with_user)
    builder.add_node("write_research_brief", write_research_brief)
    builder.add_node("research_supervisor", supervisor_subgraph)
    builder.add_node("final_report_generation", final_report_generation)

    # 定义标准流程边
    builder.add_edge(START, "clarify_with_user")
    builder.add_edge("research_supervisor", "final_report_generation")
    builder.add_edge("final_report_generation", END)

    logger.info("✅ 深度研究者图构建完成")
    return builder.compile()


# 创建默认图实例（从环境变量读取配置）
deep_researcher = build_deep_researcher_graph()
