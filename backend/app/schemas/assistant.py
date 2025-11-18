from typing import List, Optional
from pydantic import BaseModel, Field


class MCPServiceItem(BaseModel):
    """MCP服务项"""
    mcp_server_id: str = Field(..., description="MCP服务ID")


class KnowledgeBaseItem(BaseModel):
    """知识库项"""
    document_id: str = Field(..., description="文档ID")


class AssistantCreateRequest(BaseModel):
    """创建智能体请求"""
    name: str = Field(..., description="智能体名称", min_length=1, max_length=100)
    prompt: str = Field(..., description="智能体提示词/系统消息")
    description: Optional[str] = Field(None, description="智能体描述")
    enable_knowledge_base: bool = Field(default=False, description="是否启用知识库")
    knowledge_base: Optional[List[KnowledgeBaseItem]] = Field(None, description="关联的知识库文档")
    mcp_services: List[MCPServiceItem] = Field(default_factory=list, description="关联的MCP服务")


class AssistantUpdateRequest(BaseModel):
    """更新智能体请求"""
    name: Optional[str] = Field(None, description="智能体名称", min_length=1, max_length=100)
    prompt: Optional[str] = Field(None, description="智能体提示词/系统消息")
    description: Optional[str] = Field(None, description="智能体描述")
    is_active: Optional[bool] = Field(None, description="是否启用")
    enable_knowledge_base: Optional[bool] = Field(None, description="是否启用知识库")
    knowledge_base: Optional[List[KnowledgeBaseItem]] = Field(None, description="关联的知识库文档")
    mcp_services: Optional[List[MCPServiceItem]] = Field(None, description="关联的MCP服务")


class AssistantResponse(BaseModel):
    """智能体响应"""
    assistant_id: str = Field(..., description="智能体ID")
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., description="智能体名称")
    prompt: str = Field(..., description="智能体提示词")
    description: Optional[str] = Field(None, description="智能体描述")
    is_active: bool = Field(..., description="是否启用")
    enable_knowledge_base: bool = Field(..., description="是否启用知识库")
    created_at: int = Field(..., description="创建时间戳")
    updated_at: int = Field(..., description="更新时间戳")
    knowledge_base: List[KnowledgeBaseItem] = Field(default_factory=list, description="关联的知识库")
    mcp_services: List[MCPServiceItem] = Field(default_factory=list, description="关联的MCP服务")


class AssistantListResponse(BaseModel):
    """智能体列表响应"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    assistants: List[AssistantResponse] = Field(..., description="智能体列表")


class AssistantDeleteResponse(BaseModel):
    """删除智能体响应"""
    status: str = Field(..., description="操作状态")
    message: str = Field(..., description="操作消息")


class AssistantDetailResponse(BaseModel):
    """智能体详情响应"""
    assistant_id: str = Field(..., description="智能体ID")
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., description="智能体名称")
    prompt: str = Field(..., description="智能体提示词")
    description: Optional[str] = Field(None, description="智能体描述")
    is_active: bool = Field(..., description="是否启用")
    enable_knowledge_base: bool = Field(..., description="是否启用知识库")
    created_at: int = Field(..., description="创建时间戳")
    updated_at: int = Field(..., description="更新时间戳")
    knowledge_base: List[KnowledgeBaseItem] = Field(default_factory=list, description="关联的知识库")
    mcp_services: List[MCPServiceItem] = Field(default_factory=list, description="关联的MCP服务")
