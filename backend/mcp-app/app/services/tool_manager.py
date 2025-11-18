"""
工具管理器
"""
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

from app.models.tool_models import (
    ToolDefinition, ToolRegistry, ToolStatus, ToolType
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        self.registry = ToolRegistry()
        self.config_file = Path("../configs/mcp_service/tools.json")
        self.servers_config_file = Path("../configs/mcp_service/mcp_servers.json")
        self.load_tools_from_config()
    
    def load_tools_from_config(self):
        """从配置文件加载工具"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                tools_data = config_data.get("tools", [])
                for tool_data in tools_data:
                    try:
                        tool = ToolDefinition(**tool_data)
                        self.registry.add_tool(tool)
                        logger.info(f"Loaded tool: {tool.name}")
                    except Exception as e:
                        logger.error(f"Failed to load tool {tool_data.get('name', 'unknown')}: {e}")
                
                logger.info(f"Loaded {len(tools_data)} tools from config")
            else:
                logger.warning(f"Tools config file not found: {self.config_file}")
                
        except Exception as e:
            logger.error(f"Failed to load tools config: {e}")
    
    async def discover_tools_from_servers(self):
        """从MCP服务器动态发现工具"""
        try:
            if not self.servers_config_file.exists():
                logger.warning("MCP servers config file not found")
                return
            
            with open(self.servers_config_file, 'r', encoding='utf-8') as f:
                servers_config = json.load(f)
            
            servers = servers_config.get("servers", {})
            
            for server_id, server_config in servers.items():
                if not server_config.get("is_active", False):
                    continue
                
                if server_config.get("type") == "sse":
                    await self._discover_tools_from_sse_server(server_id, server_config)
                
        except Exception as e:
            logger.error(f"Failed to discover tools from servers: {e}")
    
    async def discover_tools_from_server(self, server_id: str):
        """从指定MCP服务器动态发现工具"""
        try:
            # 通过server_manager获取服务器配置
            if hasattr(self, 'server_manager') and self.server_manager:
                server = self.server_manager.get_server(server_id)
                if not server:
                    logger.warning(f"Server {server_id} not found")
                    return
                
                if not server.is_active:
                    logger.info(f"Server {server_id} is not active, skipping tool discovery")
                    return
                
                # 特殊处理：PostgreSQL服务器
                if server_id == "postgres-server":
                    await self._discover_tools_from_postgres_server(server_id)
                    logger.info(f"Completed PostgreSQL tool discovery for server {server_id}")
                    return
                
                # 将服务器对象转换为配置字典格式
                server_config = {
                    "id": server.id,
                    "name": server.name,
                    "type": server.type.value if hasattr(server.type, 'value') else str(server.type),
                    "url": server.url,
                    "is_active": server.is_active,
                    "timeout": server.timeout
                }
                
                if server_config.get("type") == "sse":
                    await self._discover_tools_from_sse_server(server_id, server_config)
                    logger.info(f"Completed tool discovery for server {server_id}")
                else:
                    logger.warning(f"Tool discovery not supported for server type: {server_config.get('type')}")
            else:
                logger.error("Server manager not available for tool discovery")
                
        except Exception as e:
            logger.error(f"Failed to discover tools from server {server_id}: {e}")
    
    async def _discover_tools_from_sse_server(self, server_id: str, server_config: dict):
        """从SSE服务器发现工具"""
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            
            url = server_config.get("url")
            if not url:
                logger.warning(f"No URL configured for server {server_id}")
                return
            
            if not url.endswith('/sse'):
                url = url.rstrip('/') + '/sse'
            
            logger.info(f"Discovering tools from server: {server_id} at {url}")
            
            async with sse_client(url=url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    # 获取工具列表
                    tools_result = await session.list_tools()
                    
                    # 如果成功获取工具，说明连接正常，更新服务器状态
                    if tools_result.tools:
                        logger.info(f"Successfully discovered {len(tools_result.tools)} tools from server {server_id}")
                        # 更新服务器状态为active
                        from app.services.server_manager import ServerStatus
                        if hasattr(self, 'server_manager') and self.server_manager:
                            self.server_manager.update_server_status(server_id, ServerStatus.active)
                            logger.info(f"Updated server {server_id} status to active")
                    
                    for mcp_tool in tools_result.tools:
                        # 转换为我们的工具定义格式
                        try:
                            input_schema = {}
                            if hasattr(mcp_tool, 'inputSchema') and mcp_tool.inputSchema:
                                if hasattr(mcp_tool.inputSchema, 'model_dump'):
                                    input_schema = mcp_tool.inputSchema.model_dump()
                                elif hasattr(mcp_tool.inputSchema, 'dict'):
                                    input_schema = mcp_tool.inputSchema.dict()
                                else:
                                    input_schema = dict(mcp_tool.inputSchema)
                            else:
                                input_schema = {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            
                            tool_definition = ToolDefinition(
                                id=f"{server_id}_{mcp_tool.name}",
                                name=mcp_tool.name,
                                description=mcp_tool.description or f"Tool from {server_id}",
                                version="1.0.0",
                                type=ToolType.http,
                                config={
                                    "server_id": server_id,
                                    "url": server_config.get("url"),
                                    "timeout": server_config.get("timeout", 60),
                                    "server_type": "sse"
                                },
                                input_schema=input_schema,
                                tags=["mcp", "discovered", server_id],
                                category="mcp_tools",
                                author=f"MCP Server: {server_id}",
                                status=ToolStatus.active
                            )
                        except Exception as tool_error:
                            logger.error(f"Failed to create tool definition for {mcp_tool.name}: {tool_error}")
                            continue
                        
                        # 添加到注册表
                        self.registry.add_tool(tool_definition)
                        logger.info(f"Discovered tool: {tool_definition.name} from server {server_id}")
                    
                    # 工具发现完成后，保存配置
                    if tools_result.tools:
                        self.save_tools_to_config()
                        logger.info(f"Saved discovered tools from server {server_id} to config")
                    
        except Exception as e:
            logger.error(f"Failed to discover tools from SSE server {server_id}: {e}")
    
    async def _discover_tools_from_postgres_server(self, server_id: str):
        """从PostgreSQL服务器发现工具"""
        try:
            logger.info(f"Discovering tools from PostgreSQL server: {server_id}")
            
            # 从server_manager获取PostgreSQL服务器
            if not hasattr(self, 'server_manager') or not self.server_manager:
                logger.error("Server manager not available")
                return
            
            if not hasattr(self.server_manager, 'postgres_server') or not self.server_manager.postgres_server:
                logger.error("PostgreSQL server not initialized in server_manager")
                return
            
            # 获取工具列表
            tools = self.server_manager.postgres_server.get_tools()
            
            logger.info(f"Found {len(tools)} tools from PostgreSQL server")
            
            # 注册每个工具
            for tool in tools:
                # 检查是否已存在
                if tool.id in self.registry.tools:
                    logger.info(f"Tool {tool.id} already registered, updating...")
                    self.registry.tools[tool.id] = tool
                else:
                    self.registry.add_tool(tool)
                
                logger.info(f"Registered PostgreSQL tool: {tool.name}")
            
            # 保存配置
            if tools:
                self.save_tools_to_config()
                logger.info(f"Saved {len(tools)} PostgreSQL tools to config")
                
        except Exception as e:
            logger.error(f"Failed to discover tools from PostgreSQL server: {e}", exc_info=True)
    
    def save_tools_to_config(self):
        """保存工具配置到文件"""
        try:
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备配置数据
            config_data = {
                "tools": [tool.dict() for tool in self.registry.tools.values()]
            }
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.registry.tools)} tools to config")
            
        except Exception as e:
            logger.error(f"Failed to save tools config: {e}")
    
    def add_tool(self, tool: ToolDefinition) -> bool:
        """添加工具"""
        try:
            # 检查工具ID是否已存在
            if tool.id in self.registry.tools:
                logger.warning(f"Tool with ID {tool.id} already exists")
                return False
            
            # 添加到注册表
            self.registry.add_tool(tool)
            
            # 保存配置
            self.save_tools_to_config()
            
            logger.info(f"Added tool: {tool.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add tool: {e}")
            return False
    
    def update_tool(self, tool_id: str, updates: Dict[str, Any]) -> bool:
        """更新工具"""
        try:
            tool = self.registry.get_tool(tool_id)
            if not tool:
                logger.warning(f"Tool {tool_id} not found")
                return False
            
            # 更新工具属性
            for key, value in updates.items():
                if hasattr(tool, key):
                    setattr(tool, key, value)
            
            # 保存配置
            self.save_tools_to_config()
            
            logger.info(f"Updated tool: {tool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update tool: {e}")
            return False
    
    def remove_tool(self, tool_id: str) -> bool:
        """删除工具"""
        try:
            success = self.registry.remove_tool(tool_id)
            if success:
                # 保存配置
                self.save_tools_to_config()
                logger.info(f"Removed tool: {tool_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove tool: {e}")
            return False
    
    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """获取工具"""
        return self.registry.get_tool(tool_id)
    
    def get_all_tools(self) -> List[ToolDefinition]:
        """获取所有工具"""
        return list(self.registry.tools.values())
    
    def get_active_tools(self) -> List[ToolDefinition]:
        """获取活跃工具"""
        return self.registry.get_active_tools()
    
    def get_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """根据分类获取工具"""
        return self.registry.get_tools_by_category(category)
    
    def get_tools_by_tag(self, tag: str) -> List[ToolDefinition]:
        """根据标签获取工具"""
        return self.registry.get_tools_by_tag(tag)
    
    def search_tools(self, query: str) -> List[ToolDefinition]:
        """搜索工具"""
        return self.registry.search_tools(query)
    
    def enable_tool(self, tool_id: str) -> bool:
        """启用工具"""
        return self.update_tool(tool_id, {"status": ToolStatus.active})
    
    def disable_tool(self, tool_id: str) -> bool:
        """禁用工具"""
        return self.update_tool(tool_id, {"status": ToolStatus.inactive})
    
    def get_tool_categories(self) -> List[str]:
        """获取工具分类列表"""
        return self.registry.categories
    
    def get_tool_tags(self) -> List[str]:
        """获取工具标签列表"""
        return self.registry.tags
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """获取工具统计信息"""
        total_tools = len(self.registry.tools)
        active_tools = len(self.registry.get_active_tools())
        inactive_tools = total_tools - active_tools
        
        # 按分类统计
        category_stats = {}
        for category in self.registry.categories:
            category_stats[category] = len(self.registry.get_tools_by_category(category))
        
        # 按标签统计
        tag_stats = {}
        for tag in self.registry.tags:
            tag_stats[tag] = len(self.registry.get_tools_by_tag(tag))
        
        return {
            "total_tools": total_tools,
            "active_tools": active_tools,
            "inactive_tools": inactive_tools,
            "categories": category_stats,
            "tags": tag_stats
        }
    
    def reload_config(self) -> bool:
        """重新加载配置文件"""
        try:
            # 清空当前注册表
            self.registry = ToolRegistry()
            
            # 重新加载
            self.load_tools_from_config()
            
            logger.info("Tools config reloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload tools config: {e}")
            return False
    
    def export_config(self) -> Dict[str, Any]:
        """导出工具配置"""
        return {
            "tools": [tool.dict() for tool in self.registry.tools.values()],
            "categories": self.registry.categories,
            "tags": self.registry.tags
        }
    
    def import_config(self, config_data: Dict[str, Any]) -> bool:
        """导入工具配置"""
        try:
            # 清空当前注册表
            self.registry = ToolRegistry()
            
            # 导入工具
            tools_data = config_data.get("tools", [])
            for tool_data in tools_data:
                try:
                    tool = ToolDefinition(**tool_data)
                    self.registry.add_tool(tool)
                except Exception as e:
                    logger.error(f"Failed to import tool {tool_data.get('name', 'unknown')}: {e}")
            
            # 保存到配置文件
            self.save_tools_to_config()
            
            logger.info(f"Imported {len(tools_data)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import tools config: {e}")
            return False
