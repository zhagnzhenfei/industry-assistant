"""
Text2SQL工具包装器
将Text2SQL LangGraph包装成LangChain工具供研究者智能体使用
"""
import logging
from typing import Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from .text2sql_graph import build_text2sql_graph
from .text2sql_nodes import initialize_mcp_client
from services.database.mcp_postgres_client import MCPPostgresClient

logger = logging.getLogger(__name__)

# 全局图实例（懒加载）
_text2sql_graph = None
_mcp_client_initialized = False


def _ensure_initialized():
    """确保Text2SQL图和MCP客户端已初始化"""
    global _text2sql_graph, _mcp_client_initialized
    
    if not _mcp_client_initialized:
        # 初始化MCP客户端
        client = MCPPostgresClient()
        initialize_mcp_client(client)
        _mcp_client_initialized = True
        logger.info("MCP客户端已初始化")
    
    if _text2sql_graph is None:
        # 构建图
        _text2sql_graph = build_text2sql_graph()
        logger.info("Text2SQL图已构建")


@tool
async def query_database(
    question: str,
    database: Optional[str] = None,
    config: RunnableConfig = None
) -> str:
    """
    查询研报数据库获取精确的统计数据和结构化信息。
    
    📊 数据库包含：
    - 公司信息（上市公司、行业、市值等）
    - 研究报告（标题、评级、目标价、发布日期等）
    - 分析师信息（姓名、机构、专长领域等）
    - 行业分类（行业名称、市场规模、增长率等）
    
    🎯 何时使用此工具：
    当问题涉及以下内容时，必须使用此工具：
    - ✅ 研报数量、评级分布、统计数据
    - ✅ 公司的市值、行业、研报数量
    - ✅ 分析师发布的研报数量和评级
    - ✅ 行业的公司数量、市场规模
    - ✅ 任何需要精确数字的问题
    - ✅ 时间范围内的统计（如"2024年"、"最近一年"）
    - ✅ 聚合分析（"多少"、"分布"、"排名"、"前N个"）
    
    📝 示例问题：
    - "2024年互联网行业的研报评级分布如何？" → 使用此工具
    - "2023年发布了多少篇研报？" → 使用此工具
    - "哪些公司获得买入评级最多？" → 使用此工具
    - "各个行业的公司数量？" → 使用此工具
    - "中金公司的分析师有哪些？" → 使用此工具
    
    Args:
        question: 要查询的问题（自然语言）
        database: 数据库名（可选）
        config: 运行时配置（可选）
    
    Returns:
        查询结果，包含SQL语句和数据
    
    Example:
        >>> result = await query_database("2023年发布了多少篇研报？")
        >>> print(result)
        查询成功！
        
        SQL: SELECT COUNT(*) FROM research_reports 
             WHERE publish_date >= '2023-01-01' 
               AND publish_date < '2024-01-01'
        
        结果: 2023年共发布了45篇研报。
    """
    logger.info(f"收到Text2SQL查询: {question}")
    
    try:
        # 确保已初始化
        _ensure_initialized()
        
        # 准备初始状态
        initial_state = {
            "question": question,
            "database": database,
            "current_attempt": 1,
            "success": False,
            "execution_attempts": []
        }
        
        # 执行图
        final_state = await _text2sql_graph.ainvoke(initial_state)
        
        # 格式化结果
        return _format_result(final_state)
        
    except Exception as e:
        logger.error(f"Text2SQL查询失败: {e}", exc_info=True)
        return f"❌ 查询失败: {str(e)}"


def _format_result(state: dict) -> str:
    """
    格式化查询结果
    
    Args:
        state: 最终状态
        
    Returns:
        格式化的结果字符串
    """
    if state.get("success"):
        # 成功情况
        sql = state.get("generated_sql", "N/A")
        results = state.get("final_results", [])
        attempts = len(state.get("execution_attempts", []))
        
        # 构建结果字符串
        output = "✅ 查询成功！\n\n"
        output += f"**SQL语句**:\n```sql\n{sql}\n```\n\n"
        output += f"**结果数量**: {len(results)} 行\n\n"
        
        # 显示结果（最多显示前10行）
        if results:
            output += "**查询结果** (前10行):\n"
            
            # 获取列名
            if results:
                columns = list(results[0].keys())
                
                # 表头
                output += "| " + " | ".join(columns) + " |\n"
                output += "| " + " | ".join(["---"] * len(columns)) + " |\n"
                
                # 数据行（最多10行）
                for row in results[:10]:
                    values = [str(row.get(col, "")) for col in columns]
                    output += "| " + " | ".join(values) + " |\n"
                
                if len(results) > 10:
                    output += f"\n*（还有{len(results) - 10}行未显示）*\n"
        else:
            output += "**查询结果**: 无数据\n"
        
        # 如果重试过，显示重试信息
        if attempts > 1:
            output += f"\n*（经过{attempts}次尝试后成功）*\n"
        
        return output
    
    else:
        # 失败情况
        attempts = state.get("execution_attempts", [])
        last_error = state.get("last_error", {})
        
        output = f"❌ 查询失败（尝试了{len(attempts)}次）\n\n"
        
        # 显示最后一次错误
        if last_error:
            output += "**最后一次错误**:\n"
            output += f"- 错误类型: {last_error.get('error_type', 'unknown')}\n"
            output += f"- 错误信息: {last_error.get('error_message', 'N/A')}\n"
            
            if last_error.get('hint'):
                output += f"- 提示: {last_error['hint']}\n"
            
            if last_error.get('sql'):
                output += f"\n尝试的SQL:\n```sql\n{last_error['sql']}\n```\n"
        
        # 显示所有尝试记录
        if len(attempts) > 1:
            output += "\n**尝试历史**:\n"
            for i, attempt in enumerate(attempts, 1):
                output += f"{i}. {attempt.get('sql', 'N/A')[:80]}... "
                if attempt.get('success'):
                    output += "✓\n"
                else:
                    output += "✗\n"
        
        return output


# 便捷函数：直接调用（用于测试）
async def query_database_simple(question: str) -> dict:
    """
    简化的查询接口（返回原始状态）
    
    Args:
        question: 问题
        
    Returns:
        完整的状态字典
    """
    _ensure_initialized()
    
    initial_state = {
        "question": question,
        "current_attempt": 1,
        "success": False,
        "execution_attempts": []
    }
    
    return await _text2sql_graph.ainvoke(initial_state)

