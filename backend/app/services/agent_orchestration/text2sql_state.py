"""
Text2SQL智能体状态定义
用于LangGraph的状态管理
"""
from typing import TypedDict, List, Dict, Any, Optional


class Text2SQLState(TypedDict, total=False):
    """
    Text2SQL智能体的状态
    
    包含从输入到输出的完整流程状态
    """
    
    # ===== 输入 =====
    question: str  # 用户的自然语言问题
    database: Optional[str]  # 数据库名（可选）
    
    # ===== Phase 1: 表选择 =====
    all_tables: List[Dict[str, Any]]  # 所有可用的表信息
    selected_tables: List[str]  # 选中的相关表名列表
    table_selection_reason: str  # 选择这些表的原因
    
    # ===== Phase 2: Schema获取 =====
    schemas: str  # 选中表的详细schema（DDL格式）
    
    # ===== Phase 3: SQL生成 =====
    generated_sql: str  # 生成的SQL语句
    sql_explanation: str  # SQL解释
    
    # ===== Phase 4: 执行与错误处理 =====
    execution_attempts: List[Dict[str, Any]]  # 所有执行尝试的记录
    current_attempt: int  # 当前是第几次尝试
    last_error: Optional[Dict[str, Any]]  # 最近一次的错误信息
    
    # ===== Phase 5: 最终结果 =====
    final_results: Optional[List[Dict[str, Any]]]  # 查询结果数据
    final_explanation: str  # 结果的自然语言解释
    success: bool  # 是否成功


class SimplifiedText2SQLState(TypedDict, total=False):
    """
    简化版Text2SQL状态（用于快速MVP）
    
    只包含核心必需的状态字段
    """
    
    # 输入
    question: str
    
    # 中间状态
    selected_tables: List[str]
    schemas: str
    generated_sql: str
    
    # 错误处理
    current_attempt: int
    last_error: Optional[Dict[str, Any]]
    
    # 输出
    final_results: Optional[List[Dict[str, Any]]]
    success: bool

