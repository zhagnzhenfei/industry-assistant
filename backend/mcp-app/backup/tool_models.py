"""
工具数据模型
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class ToolType(str, Enum):
    """工具类型"""
    function = "function"      # 函数调用
    http = "http"             # HTTP服务
    stdio = "stdio"           # 标准输入输出
    websocket = "websocket"   # WebSocket服务
    custom = "custom"         # 自定义类型

class ToolStatus(str, Enum):
    """工具状态"""
    active = "active"         # 活跃
    inactive = "inactive"     # 非活跃
    error = "error"           # 错误状态

class ServerType(str, Enum):
    """服务器类型"""
    sse = "sse"              # Server-Sent Events
    stdio = "stdio"          # 标准输入输出
    http = "http"            # HTTP服务
    websocket = "websocket"   # WebSocket服务

class ServerStatus(str, Enum):
    """服务器状态"""
    active = "active"         # 活跃
    inactive = "inactive"     # 非活跃
    error = "error"           # 错误状态
    connecting = "connecting" # 连接中

class ToolDefinition(BaseModel):
    """工具定义"""
    
    id: str = Field(..., description="工具唯一标识")
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    version: str = Field(default="1.0.0", description="工具版本")
    
    # 工具类型和配置
    type: ToolType = Field(..., description="工具类型")
    config: Dict[str, Any] = Field(..., description="工具配置")
    
    # 输入输出模式
    input_schema: Dict[str, Any] = Field(..., description="输入模式")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="输出模式")
    
    # 元数据
    tags: List[str] = Field(default_factory=list, description="标签")
    category: Optional[str] = Field(default=None, description="分类")
    author: Optional[str] = Field(default=None, description="作者")
    
    # 状态信息
    status: ToolStatus = Field(default=ToolStatus.inactive, description="工具状态")
    last_used: Optional[str] = Field(default=None, description="最后使用时间")
    usage_count: int = Field(default=0, description="使用次数")
    
    @field_validator('config')
    @classmethod
    def validate_config(cls, v):
        """验证工具配置"""
        if not isinstance(v, dict):
            raise ValueError("工具配置必须是字典类型")
        return v
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    def update_status(self, status: ToolStatus):
        """更新工具状态"""
        self.status = status
    
    def increment_usage(self):
        """增加使用次数"""
        self.usage_count += 1

class ToolExecutionRequest(BaseModel):
    """工具执行请求"""
    
    tool_id: str = Field(..., description="工具ID")
    arguments: Dict[str, Any] = Field(..., description="执行参数")
    request_id: Optional[str] = Field(default=None, description="请求ID")
    timeout: Optional[int] = Field(default=60, description="超时时间(秒)")
    
    @field_validator('arguments')
    @classmethod
    def validate_arguments(cls, v):
        """验证参数"""
        if not isinstance(v, dict):
            raise ValueError("参数必须是字典类型")
        return v

class ToolExecutionResult(BaseModel):
    """工具执行结果"""
    
    request_id: str = Field(..., description="请求ID")
    tool_id: str = Field(..., description="工具ID")
    success: bool = Field(..., description="是否成功")
    
    # 结果数据
    data: Optional[Any] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    
    # 执行信息
    execution_time: float = Field(..., description="执行时间(秒)")
    timestamp: str = Field(..., description="执行时间戳")
    
    @property
    def is_success(self) -> bool:
        """是否执行成功"""
        return self.success

class MCPServer(BaseModel):
    """MCP服务器定义"""
    
    id: str = Field(..., description="服务器唯一标识")
    name: str = Field(..., description="服务器名称")
    description: Optional[str] = Field(default=None, description="服务器描述")
    type: ServerType = Field(..., description="服务器类型")
    
    # 连接配置
    url: Optional[str] = Field(default=None, description="服务器URL（SSE/HTTP/WebSocket）")
    command: Optional[str] = Field(default=None, description="启动命令（stdio）")
    args: Optional[List[str]] = Field(default=None, description="命令参数（stdio）")
    env: Optional[Dict[str, str]] = Field(default=None, description="环境变量")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP头部")
    
    # 状态和配置
    is_active: bool = Field(default=True, description="是否激活")
    status: ServerStatus = Field(default=ServerStatus.inactive, description="服务器状态")
    timeout: int = Field(default=60, description="超时时间（秒）")
    
    # 元数据
    version: str = Field(default="1.0.0", description="版本")
    author: Optional[str] = Field(default=None, description="作者")
    tags: List[str] = Field(default_factory=list, description="标签")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    last_connected: Optional[str] = Field(default=None, description="最后连接时间")
    

    
    def update_status(self, status: ServerStatus):
        """更新服务器状态"""
        self.status = status
    
    def is_available(self) -> bool:
        """检查服务器是否可用"""
        return self.is_active and self.status in [ServerStatus.active, ServerStatus.connecting]

class ToolRegistry(BaseModel):
    """工具注册表"""
    
    tools: Dict[str, ToolDefinition] = Field(default_factory=dict, description="工具字典")
    categories: List[str] = Field(default_factory=list, description="工具分类")
    tags: List[str] = Field(default_factory=list, description="所有标签")
    
    def add_tool(self, tool: ToolDefinition):
        """添加工具"""
        self.tools[tool.id] = tool
        
        # 更新分类和标签
        if tool.category and tool.category not in self.categories:
            self.categories.append(tool.category)
        
        for tag in tool.tags:
            if tag not in self.tags:
                self.tags.append(tag)
    
    def remove_tool(self, tool_id: str) -> bool:
        """删除工具"""
        if tool_id in self.tools:
            del self.tools[tool_id]
            return True
        return False
    
    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """获取工具"""
        return self.tools.get(tool_id)
    
    def get_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """根据分类获取工具"""
        return [tool for tool in self.tools.values() if tool.category == category]
    
    def get_tools_by_tag(self, tag: str) -> List[ToolDefinition]:
        """根据标签获取工具"""
        return [tool for tool in self.tools.values() if tag in tool.tags]
    
    def get_active_tools(self) -> List[ToolDefinition]:
        """获取活跃工具"""
        return [tool for tool in self.tools.values() if tool.status == ToolStatus.active]
    
    def search_tools(self, query: str) -> List[ToolDefinition]:
        """搜索工具"""
        query_lower = query.lower()
        results = []
        
        for tool in self.tools.values():
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower() or
                any(query_lower in tag.lower() for tag in tool.tags)):
                results.append(tool)
        
        return results
