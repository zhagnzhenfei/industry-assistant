"""
Open Deep Research 配置管理
基于官方文档的完整配置系统
"""
import os
from enum import Enum
from typing import Any, List, Optional
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field


class SearchAPI(Enum):
    """可用的搜索API提供商枚举"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    TAVILY = "tavily"
    SERPER = "serper"
    NONE = "none"


class MCPConfig(BaseModel):
    """模型上下文协议(MCP)服务器配置"""
    url: Optional[str] = Field(
        default=None,
        description="MCP服务器的URL（用于http/sse传输）"
    )
    command: Optional[str] = Field(
        default=None,
        description="启动命令（用于stdio传输）"
    )
    args: Optional[List[str]] = Field(
        default_factory=list,
        description="命令参数（用于stdio传输）"
    )
    transport: str = Field(
        default="http",
        description="传输协议（http, sse, stdio, websocket）"
    )
    env: Optional[dict] = Field(
        default_factory=dict,
        description="环境变量（用于stdio传输）"
    )
    auth_required: Optional[bool] = Field(
        default=False,
        description="MCP服务器是否需要身份验证"
    )


class Configuration(BaseModel):
    """深度研究智能体的主配置类"""
    
    # 一般配置
    max_structured_output_retries: int = Field(
        default=3,
        description="模型结构化输出调用的最大重试次数"
    )
    allow_clarification: bool = Field(
        default=True,
        description="是否允许研究者在开始研究前向用户询问澄清问题"
    )
    max_concurrent_research_units: int = Field(
        default=2,  # 降低从5到2，减少并行研究者数量（关键成本控制！）
        description="最大并发研究单元数。这将允许研究者使用多个子智能体进行研究。注意：并发数越多，可能会遇到速率限制。"
    )
    
    # 研究配置
    search_api: SearchAPI = Field(
        default=SearchAPI.SERPER,
        description="用于研究的搜索API。注意：确保您的研究者模型支持所选的搜索API。"
    )
    max_researcher_iterations: int = Field(
        default=2,  # 降低从3到2，减少规划轮次
        description="研究监督者的最大研究迭代次数。这是研究监督者反思研究并提出后续问题的次数。"
    )
    max_react_tool_calls: int = Field(
        default=3,  # 降低从5到3，更严格的限制
        description="单个研究者步骤中最大工具调用迭代次数。"
    )
    max_total_searches_per_researcher: int = Field(
        default=5,  # 降低从8到5，减少搜索次数
        description="每个研究者允许的最大总搜索次数（防止过度搜索）。"
    )
    max_searches_per_iteration: int = Field(
        default=1,  # 降低从2到1，每轮只搜索一次
        description="每轮迭代中允许的最大并行搜索数量。"
    )
    
    # 模型配置
    summarization_model: str = Field(
        default="qwen-plus",
        description="用于总结Tavily搜索结果的研究结果模型"
    )
    summarization_model_max_tokens: int = Field(
        default=8192,
        description="摘要模型的最大输出token数"
    )
    max_content_length: int = Field(
        default=50000,
        description="摘要前网页内容的最大字符长度"
    )
    research_model: str = Field(
        default="qwen-plus",
        description="用于进行研究的模型。注意：确保您的研究者模型支持所选的搜索API。"
    )
    research_model_max_tokens: int = Field(
        default=10000,
        description="研究模型的最大输出token数"
    )
    compression_model: str = Field(
        default="qwen-plus",
        description="用于压缩子智能体研究发现的模型。注意：确保您的压缩模型支持所选的搜索API。"
    )
    compression_model_max_tokens: int = Field(
        default=8192,
        description="压缩模型的最大输出token数"
    )
    final_report_model: str = Field(
        default="qwen-plus",
        description="用于从所有研究发现编写最终报告的模型"
    )
    final_report_model_max_tokens: int = Field(
        default=10000,
        description="最终报告模型的最大输出token数"
    )
    
    # MCP服务器配置
    mcp_config: Optional[MCPConfig] = Field(
        default=None,
        optional=True,
        description="MCP服务器配置"
    )
    mcp_prompt: Optional[str] = Field(
        default=None,
        optional=True,
        description="向智能体传递的有关可用MCP工具的任何其他说明。"
    )

    # MCP工具集成配置
    mcp_enabled: bool = Field(
        default=True,
        description="是否启用MCP工具集成"
    )
    mcp_server_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="要集成的MCP服务器ID列表，为空表示集成所有可用服务器"
    )
    mcp_timeout: int = Field(
        default=30,
        description="MCP服务器连接超时时间（秒）"
    )
    mcp_retry_count: int = Field(
        default=3,
        description="MCP服务器连接失败重试次数"
    )
    mcp_cache_enabled: bool = Field(
        default=True,
        description="是否启用MCP工具缓存"
    )
    mcp_cache_ttl: int = Field(
        default=300,
        description="MCP工具缓存生存时间（秒）"
    )
    
    # Text2SQL配置
    text2sql_enabled: bool = Field(
        default=True,
        description="是否启用Text2SQL工具（结构化数据库查询）"
    )
    text2sql_max_retries: int = Field(
        default=3,
        description="SQL生成失败时的最大重试次数"
    )
    text2sql_top_k_results: int = Field(
        default=100,
        description="SQL查询返回的最大结果行数"
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """从RunnableConfig创建Configuration实例"""
        configurable = config.get("configurable", {}) if config else {}
        field_names = list(cls.model_fields.keys())
        values: dict[str, Any] = {
            field_name: os.environ.get(field_name.upper(), configurable.get(field_name))
            for field_name in field_names
        }
        return cls(**{k: v for k, v in values.items() if v is not None})

    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True
