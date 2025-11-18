"""
Text2SQL LangGraph定义（简化版）
定义工作流的节点和边
"""
import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from .text2sql_state import SimplifiedText2SQLState
from .text2sql_nodes import (
    select_tables_node,
    generate_sql_node,
    execute_sql_node
)

logger = logging.getLogger(__name__)


def should_retry_sql(state: SimplifiedText2SQLState) -> Literal["generate_sql", "end"]:
    """
    条件路由：决定是否重试SQL生成
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    # 如果成功，结束
    if state.get("success"):
        return "end"
    
    # 如果失败但未超过重试次数（最多3次）
    current_attempt = state.get("current_attempt", 1)
    max_retries = 3
    
    if current_attempt <= max_retries:
        logger.info(f"准备重试，当前第{current_attempt}次尝试")
        return "generate_sql"
    
    # 超过重试次数，结束
    logger.warning(f"已达到最大重试次数{max_retries}，停止重试")
    return "end"


def build_text2sql_graph():
    """
    构建Text2SQL的LangGraph（简化版）
    
    工作流：
    1. select_tables - 选择相关表
    2. generate_sql - 生成SQL
    3. execute_sql - 执行SQL
    4. 如果失败且未超重试次数 -> 回到generate_sql
    5. 如果成功或超重试次数 -> 结束
    
    Returns:
        编译后的图
    """
    logger.info("构建Text2SQL LangGraph...")
    
    # 创建状态图
    graph = StateGraph(SimplifiedText2SQLState)
    
    # 添加节点
    graph.add_node("select_tables", select_tables_node)
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    
    # 定义边
    # 流程：select_tables -> generate_sql -> execute_sql
    graph.set_entry_point("select_tables")
    graph.add_edge("select_tables", "generate_sql")
    graph.add_edge("generate_sql", "execute_sql")
    
    # 条件边：execute_sql后根据结果决定下一步
    graph.add_conditional_edges(
        "execute_sql",
        should_retry_sql,
        {
            "generate_sql": "generate_sql",  # 重试
            "end": END  # 结束
        }
    )
    
    # 编译图
    compiled_graph = graph.compile()
    
    logger.info("Text2SQL LangGraph构建完成")
    
    return compiled_graph


# 可视化图（用于调试）
def visualize_graph():
    """
    可视化LangGraph结构
    
    Returns:
        Mermaid格式的图描述
    """
    graph = build_text2sql_graph()
    
    try:
        # 尝试生成Mermaid图
        mermaid = graph.get_graph().draw_mermaid()
        return mermaid
    except Exception as e:
        logger.error(f"可视化图失败: {e}")
        return """
graph TD
    A[START] --> B[select_tables]
    B --> C[generate_sql]
    C --> D[execute_sql]
    D -->|成功| E[END]
    D -->|失败且<3次| C
    D -->|失败且≥3次| E
"""

