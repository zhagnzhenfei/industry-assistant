"""
标准MCP客户端
提供简洁的MCP协议交互接口
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union

from app.models.mcp_models import (
    MCPServerConfig, MCPServerInfo, MCPTool, MCPResource, MCPPrompt,
    ConnectionStatus
)
from app.services.mcp_connection_manager import MCPConnectionManager

logger = logging.getLogger(__name__)


class MCPClient:
    """标准MCP客户端"""

    def __init__(self):
        self.connection_manager = MCPConnectionManager()

    # === 服务器管理 ===
    async def add_server(self, config: MCPServerConfig) -> bool:
        """添加MCP服务器"""
        return await self.connection_manager.add_server(config)

    async def connect_server(self, server_id: str) -> bool:
        """连接到MCP服务器"""
        return await self.connection_manager.connect_server(server_id)

    async def disconnect_server(self, server_id: str):
        """断开MCP服务器"""
        await self.connection_manager.disconnect_server(server_id)

    async def remove_server(self, server_id: str) -> bool:
        """移除MCP服务器"""
        if server_id in self.connection_manager.connections:
            await self.disconnect_server(server_id)
            del self.connection_manager.connections[server_id]
            logger.info(f"移除服务器: {server_id}")
            return True
        return False

    # === 服务器查询 ===
    def get_server(self, server_id: str) -> Optional[MCPServerInfo]:
        """获取服务器信息"""
        return self.connection_manager.get_server_info(server_id)

    def get_servers(self, status: Optional[ConnectionStatus] = None) -> List[MCPServerInfo]:
        """获取服务器列表"""
        servers = self.connection_manager.get_all_servers()
        if status:
            return [s for s in servers if s.status == status]
        return servers

    def get_active_servers(self) -> List[MCPServerInfo]:
        """获取活跃服务器"""
        return self.connection_manager.get_active_servers()

    # === 工具操作 ===
    async def call_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        try:
            logger.info(f"🚀 调用工具: {server_id}.{tool_name}, 参数: {arguments}")
            result = await self.connection_manager.call_tool(server_id, tool_name, arguments)
            logger.info(f"✅ 工具调用成功: {server_id}.{tool_name}")
            return result
        except Exception as e:
            logger.error(f"❌ 工具调用失败: {server_id}.{tool_name}, 错误: {e}")
            raise

    def get_tools(self, server_id: Optional[str] = None) -> List[MCPTool]:
        """获取工具列表"""
        if server_id:
            server_info = self.get_server(server_id)
            return server_info.tools if server_info else []
        else:
            # 获取所有服务器的工具
            all_tools = []
            for server_info in self.get_servers(ConnectionStatus.CONNECTED):
                for tool in server_info.tools:
                    tool_copy = tool.model_copy()
                    tool_copy.name = f"{server_id}.{tool.name}"
                    all_tools.append(tool_copy)
            return all_tools

    def get_tool(self, server_id: str, tool_name: str) -> Optional[MCPTool]:
        """获取特定工具"""
        server_info = self.get_server(server_id)
        if not server_info:
            return None

        for tool in server_info.tools:
            if tool.name == tool_name:
                return tool
        return None

    # === 资源操作 ===
    def get_resources(self, server_id: Optional[str] = None) -> List[MCPResource]:
        """获取资源列表"""
        if server_id:
            server_info = self.get_server(server_id)
            return server_info.resources if server_info else []
        else:
            # 获取所有服务器的资源
            all_resources = []
            for server_info in self.get_servers(ConnectionStatus.CONNECTED):
                all_resources.extend(server_info.resources)
            return all_resources

    # === 提示操作 ===
    def get_prompts(self, server_id: Optional[str] = None) -> List[MCPPrompt]:
        """获取提示列表"""
        if server_id:
            server_info = self.get_server(server_id)
            return server_info.prompts if server_info else []
        else:
            # 获取所有服务器的提示
            all_prompts = []
            for server_info in self.get_servers(ConnectionStatus.CONNECTED):
                all_prompts.extend(server_info.prompts)
            return all_prompts

    # === 统计信息 ===
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        servers = self.get_servers()
        active_servers = self.get_active_servers()

        total_tools = sum(len(server.tools) for server in servers)
        active_tools = sum(len(server.tools) for server in active_servers)

        total_resources = sum(len(server.resources) for server in servers)
        total_prompts = sum(len(server.prompts) for server in servers)

        return {
            "servers": {
                "total": len(servers),
                "active": len(active_servers),
                "connecting": len([s for s in servers if s.status == ConnectionStatus.CONNECTING]),
                "error": len([s for s in servers if s.status == ConnectionStatus.ERROR])
            },
            "tools": {
                "total": total_tools,
                "active": active_tools
            },
            "resources": total_resources,
            "prompts": total_prompts,
            "servers_detail": [
                {
                    "id": server.config.id,
                    "name": server.config.name,
                    "type": server.config.type,
                    "status": server.status,
                    "tools_count": len(server.tools),
                    "resources_count": len(server.resources),
                    "prompts_count": len(server.prompts),
                    "last_connected": server.last_connected,
                    "error_message": server.error_message
                }
                for server in servers
            ]
        }

    # === 健康检查 ===
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_stats()

        # 检查是否有活跃连接
        is_healthy = stats["servers"]["active"] > 0

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "active_connections": stats["servers"]["active"],
            "total_tools": stats["tools"]["active"],
            "timestamp": str(asyncio.get_event_loop().time()),
            "details": stats
        }

    async def close(self):
        """关闭客户端"""
        await self.connection_manager.close_all()
        logger.info("MCP客户端已关闭")