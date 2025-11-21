"""
MCP协议标准模型
基于Model Context Protocol规范
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
import json


class MCPMethod(str, Enum):
    """MCP标准方法"""
    # 协议方法
    INITIALIZE = "initialize"
    PING = "ping"

    # 工具方法
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # 资源方法
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"

    # 提示方法
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"


class MCPError(BaseModel):
    """MCP错误模型"""
    code: int = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    data: Optional[Any] = Field(default=None, description="错误数据")


class MCPRequest(BaseModel):
    """MCP请求模型"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC版本")
    id: Optional[Union[str, int]] = Field(default=None, description="请求ID")
    method: MCPMethod = Field(..., description="MCP方法")
    params: Optional[Dict[str, Any]] = Field(default=None, description="方法参数")


class MCPResponse(BaseModel):
    """MCP响应模型"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC版本")
    id: Optional[Union[str, int]] = Field(default=None, description="请求ID")
    result: Optional[Any] = Field(default=None, description="响应结果")
    error: Optional[MCPError] = Field(default=None, description="错误信息")


class MCPTool(BaseModel):
    """MCP工具定义"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    inputSchema: Dict[str, Any] = Field(..., description="输入模式")


class MCPToolParameter(BaseModel):
    """MCP工具调用参数"""
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(..., description="工具参数")


class MCPResource(BaseModel):
    """MCP资源定义"""
    uri: str = Field(..., description="资源URI")
    name: str = Field(..., description="资源名称")
    description: Optional[str] = Field(default=None, description="资源描述")
    mimeType: Optional[str] = Field(default=None, description="MIME类型")


class MCPPrompt(BaseModel):
    """MCP提示定义"""
    name: str = Field(..., description="提示名称")
    description: str = Field(..., description="提示描述")
    arguments: Optional[List[Dict[str, Any]]] = Field(default=None, description="提示参数")


class MCPServerCapabilities(BaseModel):
    """MCP服务器能力"""
    tools: Optional[Dict[str, Any]] = Field(default=None, description="工具能力")
    resources: Optional[Dict[str, Any]] = Field(default=None, description="资源能力")
    prompts: Optional[Dict[str, Any]] = Field(default=None, description="提示能力")


class MCPClientInfo(BaseModel):
    """MCP客户端信息"""
    name: str = Field(..., description="客户端名称")
    version: str = Field(..., description="客户端版本")


class MCPInitializeParams(BaseModel):
    """MCP初始化参数"""
    protocolVersion: str = Field(default="2024-11-05", description="协议版本")
    capabilities: MCPServerCapabilities = Field(..., description="服务器能力")
    clientInfo: MCPClientInfo = Field(..., description="客户端信息")


# 连接相关枚举
class ConnectionType(str, Enum):
    """连接类型"""
    SSE = "sse"           # Server-Sent Events
    STDIO = "stdio"       # 标准输入输出
    HTTP = "http"         # HTTP请求
    WEBSOCKET = "websocket"  # WebSocket


class ConnectionStatus(str, Enum):
    """连接状态"""
    CONNECTING = "connecting"  # 连接中
    CONNECTED = "connected"    # 已连接
    DISCONNECTED = "disconnected"  # 已断开
    ERROR = "error"           # 错误状态


class MCPServerConfig(BaseModel):
    """MCP服务器配置"""
    id: str = Field(..., description="服务器ID")
    name: str = Field(..., description="服务器名称")
    description: Optional[str] = Field(default=None, description="服务器描述")

    # 连接配置
    type: ConnectionType = Field(..., description="连接类型")
    url: Optional[str] = Field(default=None, description="服务器URL")
    command: Optional[str] = Field(default=None, description="启动命令")
    args: Optional[List[str]] = Field(default=None, description="命令参数")
    env: Optional[Dict[str, str]] = Field(default=None, description="环境变量")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP头部")

    # 连接参数
    timeout: int = Field(default=60, description="超时时间")
    retry_count: int = Field(default=3, description="重试次数")
    is_active: bool = Field(default=True, description="是否激活")


class MCPServerInfo(BaseModel):
    """MCP服务器信息"""
    config: MCPServerConfig = Field(..., description="服务器配置")
    status: ConnectionStatus = Field(default=ConnectionStatus.DISCONNECTED, description="连接状态")
    capabilities: Optional[MCPServerCapabilities] = Field(default=None, description="服务器能力")
    tools: List[MCPTool] = Field(default_factory=list, description="可用工具")
    resources: List[MCPResource] = Field(default_factory=list, description="可用资源")
    prompts: List[MCPPrompt] = Field(default_factory=list, description="可用提示")
    last_connected: Optional[str] = Field(default=None, description="最后连接时间")
    error_message: Optional[str] = Field(default=None, description="错误信息")