"""
Open Deep Research 状态定义
基于官方文档的完整状态管理系统
"""
import operator
from typing import Annotated, Optional
from langchain_core.messages import MessageLikeRepresentation
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


###################
# 结构化输出定义
###################
class ConductResearch(BaseModel):
    """调用此工具对特定主题进行研究"""
    research_topic: str = Field(
        description="要研究的主题。应该是单个主题，并且应该详细描述（至少一段话）。",
    )


class ResearchComplete(BaseModel):
    """调用此工具表示研究已完成"""


class Summary(BaseModel):
    """研究摘要与关键发现"""
    summary: str
    key_excerpts: str


class ClarifyWithUser(BaseModel):
    """用户澄清请求模型"""
    need_clarification: bool = Field(
        description="是否需要向用户询问澄清问题。",
    )
    question: str = Field(
        description="向用户询问以澄清报告范围的问题",
    )
    verification: str = Field(
        description="验证消息，表示我们将在用户提供必要信息后开始研究。",
    )


class ResearchQuestion(BaseModel):
    """研究问题和简报，用于指导研究"""
    research_brief: str = Field(
        description="将用于指导研究的研究问题。",
    )


###################
# 状态定义
###################

def override_reducer(current_value, new_value):
    """允许在状态中覆盖值的归约器函数"""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)


def max_reducer(current_value: int | None, new_value: int | None) -> int:
    """取最大值的归约器函数，用于计数器以确保单调递增"""
    if current_value is None:
        return new_value or 0
    if new_value is None:
        return current_value or 0
    return max(current_value, new_value)


class AgentInputState(MessagesState):
    """输入状态只包含 'messages'"""


class AgentState(MessagesState):
    """主智能体状态，包含消息和研究数据"""
    supervisor_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    research_brief: Optional[str]
    raw_notes: Annotated[list[str], override_reducer] = []
    notes: Annotated[list[str], override_reducer] = []
    final_report: str
    
    # 记忆相关字段（可选）
    short_term_memory: Optional[list] = None  # 短期记忆（最近对话）
    user_profile: Optional[dict] = None  # 用户画像
    user_context: Optional[dict] = None  # 用户上下文（包含user_id等）


class SupervisorState(TypedDict):
    """监督者状态，管理研究任务"""
    supervisor_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    research_brief: str
    notes: Annotated[list[str], override_reducer] = []
    research_iterations: int = 0
    used_research_units: int = 0  # 已使用的研究单元数
    raw_notes: Annotated[list[str], override_reducer] = []
    decision: dict = {}  # 思考节点的决策输出（字典格式）
    previous_notes: list[str]  # 上一轮的研究发现，用于质量控制
    last_action: str  # 最后执行的动作：research 或 complete
    exit_type: str  # 退出类型：forced, quality_control, decision 等


class ResearcherState(TypedDict):
    """个体研究者状态，进行研究"""
    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    tool_call_iterations: Annotated[int, max_reducer]  # 使用max_reducer确保计数器正确递增
    total_searches: Annotated[int, max_reducer]  # 总搜索次数计数器
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[list[str], override_reducer] = []


class ResearcherOutputState(BaseModel):
    """个体研究者的输出状态"""
    compressed_research: str
    raw_notes: Annotated[list[str], override_reducer] = []
