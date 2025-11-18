"""
Text2SQL LangGraph节点实现（简化版）
每个节点处理工作流的一个阶段
"""
import logging
from typing import Dict, Any
from datetime import datetime

from .text2sql_state import SimplifiedText2SQLState
from services.database.mcp_postgres_client import MCPPostgresClient

logger = logging.getLogger(__name__)

# 全局MCP客户端（将由初始化函数设置）
mcp_client: MCPPostgresClient = None


def initialize_mcp_client(client: MCPPostgresClient):
    """初始化全局MCP客户端"""
    global mcp_client
    mcp_client = client
    logger.info("MCP客户端已初始化")


async def select_tables_node(state: SimplifiedText2SQLState) -> Dict[str, Any]:
    """
    节点1：选择相关表
    
    使用简单的关键词匹配从所有表中选择相关的表。
    """
    question = state["question"]
    
    logger.info(f"开始选择相关表，问题: {question}")
    
    try:
        # 1. 获取所有表
        all_tables = await mcp_client.list_tables()
        
        if not all_tables:
            logger.error("未找到任何表")
            return {
                **state,
                "selected_tables": [],
                "success": False
            }
        
        # 2. 简单的关键词匹配
        # 提取问题中的关键词
        question_lower = question.lower()
        selected_tables = []
        
        # 关键词到表名的映射
        keyword_mapping = {
            '公司': ['companies'],
            '企业': ['companies'],
            '分析师': ['analysts'],
            '研报': ['research_reports'],
            '报告': ['research_reports'],
            '评级': ['research_reports'],
            '行业': ['industries'],
            '主题': ['report_topics'],
        }
        
        # 根据关键词选择表
        for keyword, tables in keyword_mapping.items():
            if keyword in question_lower:
                selected_tables.extend(tables)
        
        # 去重
        selected_tables = list(set(selected_tables))
        
        # 如果没有匹配到，默认使用最相关的表
        if not selected_tables:
            # 根据问题内容智能选择
            if any(word in question_lower for word in ['多少', '数量', '统计']):
                selected_tables = ['research_reports', 'companies']
            else:
                selected_tables = ['companies']
        
        logger.info(f"选中的表: {selected_tables}")
        
        return {
            **state,
            "selected_tables": selected_tables
        }
        
    except Exception as e:
        logger.error(f"选择表失败: {e}", exc_info=True)
        return {
            **state,
            "selected_tables": [],
            "success": False
        }


async def generate_sql_node(state: SimplifiedText2SQLState) -> Dict[str, Any]:
    """
    节点2：生成SQL
    
    使用LLM根据问题和schema生成SQL查询。
    """
    question = state["question"]
    selected_tables = state["selected_tables"]
    last_error = state.get("last_error")
    
    logger.info(f"开始生成SQL，表: {selected_tables}")
    
    try:
        # 1. 获取表结构
        schemas = await mcp_client.get_schemas(selected_tables)
        
        if not schemas:
            logger.error("无法获取表结构")
            return {
                **state,
                "generated_sql": "",
                "success": False
            }
        
        # 2. 构建提示词
        prompt = _build_sql_generation_prompt(
            question=question,
            schemas=schemas,
            last_error=last_error
        )
        
        # 3. 调用LLM生成SQL
        from .qwen_model import init_qwen_model
        from langchain_core.messages import HumanMessage, SystemMessage
        import json
        import re
        
        # 使用默认配置初始化模型（会从环境变量读取TEXT2SQL_MODEL）
        model = init_qwen_model(max_tokens=1000)
        
        # 使用简单的消息调用（不使用结构化输出）
        messages = [
            SystemMessage(content="""你是一个PostgreSQL专家。根据用户问题生成SQL。

请返回JSON格式：
{
  "sql": "SELECT ...",
  "explanation": "这个查询..."
}"""),
            HumanMessage(content=prompt)
        ]
        
        try:
            result = await model.ainvoke(messages)
            content = result.content
            
            # 从返回内容中提取JSON
            # 尝试直接解析JSON
            try:
                data = json.loads(content)
                generated_sql = data.get("sql", "")
                explanation = data.get("explanation", "")
            except json.JSONDecodeError:
                # 如果不是纯JSON，尝试提取JSON块
                json_match = re.search(r'\{[^{}]*"sql"[^{}]*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    generated_sql = data.get("sql", "")
                    explanation = data.get("explanation", "")
                else:
                    # 如果找不到JSON，尝试直接提取SQL语句
                    sql_match = re.search(r'SELECT\s+.+?(?:;|$)', content, re.IGNORECASE | re.DOTALL)
                    if sql_match:
                        generated_sql = sql_match.group().strip()
                        explanation = "自动生成的查询"
                    else:
                        raise ValueError("无法从LLM响应中提取SQL")
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 返回一个简单的默认SQL
            generated_sql = f"SELECT COUNT(*) FROM companies"
            explanation = f"LLM调用失败，使用默认查询"
        
        logger.info(f"SQL生成成功: {generated_sql}")
        
        return {
            **state,
            "schemas": schemas,
            "generated_sql": generated_sql,
            "sql_explanation": explanation
        }
        
    except Exception as e:
        logger.error(f"生成SQL失败: {e}", exc_info=True)
        return {
            **state,
            "generated_sql": "",
            "success": False
        }


async def execute_sql_node(state: SimplifiedText2SQLState) -> Dict[str, Any]:
    """
    节点3：执行SQL
    
    执行生成的SQL，处理错误并记录执行结果。
    """
    sql = state["generated_sql"]
    current_attempt = state.get("current_attempt", 1)
    
    logger.info(f"执行SQL（第{current_attempt}次尝试）: {sql}")
    
    try:
        # 执行SQL
        result = await mcp_client.execute_query(sql)
        
        # 记录执行尝试
        attempt_record = {
            "attempt": current_attempt,
            "sql": sql,
            "success": result.get("success", False),
            "timestamp": datetime.now().isoformat()
        }
        
        execution_attempts = state.get("execution_attempts", [])
        execution_attempts.append(attempt_record)
        
        if result.get("success"):
            # 执行成功
            logger.info(f"SQL执行成功，返回{result.get('row_count', 0)}行")
            
            return {
                **state,
                "final_results": result.get("data", []),
                "success": True,
                "execution_attempts": execution_attempts,
                "last_error": None
            }
        else:
            # 执行失败
            error_info = {
                "error_type": result.get("error_type", "unknown"),
                "error_message": result.get("error_message", "Unknown error"),
                "hint": result.get("hint"),
                "fix_suggestions": result.get("fix_suggestions", []),
                "sql": sql
            }
            
            logger.warning(
                f"SQL执行失败（第{current_attempt}次）: "
                f"{error_info['error_message']}"
            )
            
            return {
                **state,
                "success": False,
                "last_error": error_info,
                "current_attempt": current_attempt + 1,
                "execution_attempts": execution_attempts
            }
            
    except Exception as e:
        logger.error(f"执行SQL异常: {e}", exc_info=True)
        
        error_info = {
            "error_type": "execution_exception",
            "error_message": str(e),
            "sql": sql
        }
        
        return {
            **state,
            "success": False,
            "last_error": error_info,
            "current_attempt": current_attempt + 1
        }


def _build_sql_generation_prompt(
    question: str,
    schemas: str,
    last_error: Dict[str, Any] = None
) -> str:
    """
    构建SQL生成的提示词
    
    Args:
        question: 用户问题
        schemas: 表结构
        last_error: 上次错误（如果有）
    
    Returns:
        完整的提示词
    """
    prompt = f"""你是一个PostgreSQL专家。根据用户问题和数据库schema，生成正确的SQL查询。

数据库Schema:
{schemas}

用户问题: {question}

规则:
1. 只生成SELECT查询，不要使用INSERT/UPDATE/DELETE
2. 使用提供的表名和列名，不要臆造
3. 如果需要聚合，使用GROUP BY
4. 如果需要排序，使用ORDER BY
5. 默认限制结果为100行（使用LIMIT）
6. 注意PostgreSQL语法（如使用::进行类型转换）
7. 日期格式使用 'YYYY-MM-DD'
"""
    
    # 如果有上次错误，添加错误信息
    if last_error:
        prompt += f"""

⚠️ 上次SQL执行失败，请修正错误：
- SQL: {last_error.get('sql')}
- 错误类型: {last_error.get('error_type')}
- 错误信息: {last_error.get('error_message')}
"""
        
        if last_error.get('hint'):
            prompt += f"- 提示: {last_error['hint']}\n"
        
        if last_error.get('fix_suggestions'):
            prompt += f"- 修正建议:\n"
            for suggestion in last_error['fix_suggestions']:
                prompt += f"  * {suggestion}\n"
    
    prompt += """

请生成SQL查询。
"""
    
    return prompt

