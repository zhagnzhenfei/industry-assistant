"""
MCP服务器管理器
"""
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import time
from datetime import datetime

from app.models.tool_models import MCPServer, ServerStatus, ServerType
from app.core.config import settings

logger = logging.getLogger(__name__)

class ServerManager:
    """MCP服务器管理器"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.config_file = Path("../configs/mcp_service/mcp_servers.json")
        
        # PostgreSQL服务器实例
        self.postgres_server = None
        
        self.load_servers_from_config()
    
    async def initialize_postgres_server(self):
        """初始化PostgreSQL服务器"""
        try:
            from app.services.postgres_server import PostgreSQLServer
            import os
            
            # 从环境变量读取配置
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', '5432')),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', ''),
                'database': os.getenv('POSTGRES_DB', 'postgres'),
                'max_connections': 10
            }
            
            # 创建PostgreSQL服务器
            self.postgres_server = PostgreSQLServer(
                server_id="postgres-server",
                db_config=db_config
            )
            
            # 初始化服务器（连接数据库、构建Schema图）
            await self.postgres_server.initialize()
            
            # 注册到服务器列表
            server_info = self.postgres_server.get_server_info()
            self.servers["postgres-server"] = server_info
            
            logger.info("PostgreSQL服务器初始化成功")
            
        except Exception as e:
            logger.error(f"PostgreSQL服务器初始化失败: {e}", exc_info=True)
            # 不抛出异常，允许服务继续运行
    
    def load_servers_from_config(self):
        """从配置文件加载服务器"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                servers_data = config_data.get("servers", {})
                for server_id, server_data in servers_data.items():
                    try:
                        # 确保ID一致
                        server_data["id"] = server_id
                        server = MCPServer(**server_data)
                        self.servers[server_id] = server
                        logger.info(f"Loaded server: {server.name}")
                    except Exception as e:
                        logger.error(f"Failed to load server {server_id}: {e}")
                
                logger.info(f"Loaded {len(self.servers)} servers from config")
            else:
                logger.warning(f"Servers config file not found: {self.config_file}")
                # 创建默认配置文件
                self._create_default_config()
                
        except Exception as e:
            logger.error(f"Failed to load servers config: {e}")
    
    def _create_default_config(self):
        """创建默认配置文件"""
        try:
            default_config = {
                "servers": {}
            }
            
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            logger.info("Created default servers config file")
        except Exception as e:
            logger.error(f"Failed to create default config: {e}")
    
    def save_servers_to_config(self):
        """保存服务器配置到文件"""
        try:
            logger.info(f"开始保存服务器配置到文件: {self.config_file}")
            logger.info(f"当前内存中的服务器数量: {len(self.servers)}")
            
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"配置目录确认存在: {self.config_file.parent}")
            
            # 准备配置数据
            config_data = {
                "servers": {
                    server_id: server.dict() for server_id, server in self.servers.items()
                }
            }
            
            logger.info(f"准备写入的配置数据: {json.dumps(config_data, indent=2, ensure_ascii=False)}")
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"成功保存 {len(self.servers)} 个服务器配置到文件")
            
        except Exception as e:
            logger.error(f"保存服务器配置失败: {e}", exc_info=True)
            raise
    
    def add_server(self, server: MCPServer) -> bool:
        """添加服务器"""
        try:
            # 检查服务器ID是否已存在
            if server.id in self.servers:
                logger.warning(f"Server with ID {server.id} already exists")
                return False
            
            # 设置创建时间
            server.created_at = datetime.now().isoformat()
            
            # 添加到内存
            self.servers[server.id] = server
            
            # 保存配置
            self.save_servers_to_config()
            
            logger.info(f"Added server: {server.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add server: {e}")
            return False
    
    def update_server(self, server_id: str, updates: Dict[str, Any]) -> bool:
        """更新服务器"""
        try:
            server = self.servers.get(server_id)
            if not server:
                logger.warning(f"Server {server_id} not found")
                return False
            
            # 更新服务器属性
            for key, value in updates.items():
                if hasattr(server, key):
                    setattr(server, key, value)
            
            # 保存配置
            self.save_servers_to_config()
            
            logger.info(f"Updated server: {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update server: {e}")
            return False
    
    def remove_server(self, server_id: str) -> bool:
        """删除服务器"""
        try:
            if server_id not in self.servers:
                logger.warning(f"Server {server_id} not found")
                return False
            
            # 从内存中删除
            del self.servers[server_id]
            
            # 保存配置
            self.save_servers_to_config()
            
            logger.info(f"Removed server: {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove server: {e}")
            return False
    
    def get_server(self, server_id: str) -> Optional[MCPServer]:
        """获取服务器"""
        return self.servers.get(server_id)
    
    def get_all_servers(self) -> List[MCPServer]:
        """获取所有服务器"""
        return list(self.servers.values())
    
    def get_active_servers(self) -> List[MCPServer]:
        """获取活跃服务器"""
        return [server for server in self.servers.values() if server.is_active]
    
    def get_servers_by_type(self, server_type: ServerType) -> List[MCPServer]:
        """根据类型获取服务器"""
        return [server for server in self.servers.values() if server.type == server_type]
    
    def get_servers_by_status(self, status: ServerStatus) -> List[MCPServer]:
        """根据状态获取服务器"""
        return [server for server in self.servers.values() if server.status == status]
    
    def enable_server(self, server_id: str) -> bool:
        """启用服务器"""
        return self.update_server(server_id, {"is_active": True})
    
    def disable_server(self, server_id: str) -> bool:
        """禁用服务器"""
        return self.update_server(server_id, {"is_active": False})
    
    def update_server_status(self, server_id: str, status: ServerStatus) -> bool:
        """更新服务器状态"""
        try:
            server = self.servers.get(server_id)
            if not server:
                return False
            
            server.update_status(status)
            
            # 如果连接成功，更新最后连接时间
            if status == ServerStatus.active:
                server.last_connected = datetime.now().isoformat()
            
            # 保存配置
            self.save_servers_to_config()
            
            return True
        except Exception as e:
            logger.error(f"Failed to update server status: {e}")
            return False
    
    async def test_server_connection(self, server_id: str) -> bool:
        """测试服务器连接"""
        try:
            server = self.servers.get(server_id)
            if not server:
                return False
            
            # 更新状态为连接中
            self.update_server_status(server_id, ServerStatus.connecting)
            
            if server.type == ServerType.sse:
                return await self._test_sse_server(server)
            elif server.type == ServerType.http:
                return await self._test_http_server(server)
            elif server.type == ServerType.stdio:
                return await self._test_stdio_server(server)
            else:
                logger.warning(f"Unsupported server type for testing: {server.type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to test server connection: {e}")
            self.update_server_status(server_id, ServerStatus.error)
            return False
    
    async def _test_sse_server(self, server: MCPServer) -> bool:
        """测试SSE服务器连接"""
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            
            url = server.url
            if not url.endswith('/sse'):
                url = url.rstrip('/') + '/sse'
            
            async with sse_client(url=url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    # 尝试列出工具以验证连接
                    await session.list_tools()
                    
                    # 连接成功
                    self.update_server_status(server.id, ServerStatus.active)
                    return True
                    
        except Exception as e:
            logger.error(f"SSE server test failed for {server.name}: {e}")
            self.update_server_status(server.id, ServerStatus.error)
            return False
    
    async def _test_http_server(self, server: MCPServer) -> bool:
        """测试HTTP服务器连接"""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(server.url, headers=server.headers or {})
                response.raise_for_status()
                
                # 连接成功
                self.update_server_status(server.id, ServerStatus.active)
                return True
                
        except Exception as e:
            logger.error(f"HTTP server test failed for {server.name}: {e}")
            self.update_server_status(server.id, ServerStatus.error)
            return False
    
    async def _test_stdio_server(self, server: MCPServer) -> bool:
        """测试stdio服务器连接"""
        try:
            # stdio服务器测试比较复杂，暂时标记为活跃
            # 实际使用时会在工具执行时验证
            self.update_server_status(server.id, ServerStatus.active)
            return True
            
        except Exception as e:
            logger.error(f"stdio server test failed for {server.name}: {e}")
            self.update_server_status(server.id, ServerStatus.error)
            return False
    
    def get_server_stats(self) -> Dict[str, Any]:
        """获取服务器统计信息"""
        total_servers = len(self.servers)
        active_servers = len([s for s in self.servers.values() if s.is_active])
        connected_servers = len([s for s in self.servers.values() if s.status == ServerStatus.active])
        
        # 按类型统计
        type_stats = {}
        for server_type in ServerType:
            type_stats[server_type.value] = len(self.get_servers_by_type(server_type))
        
        # 按状态统计
        status_stats = {}
        for status in ServerStatus:
            status_stats[status.value] = len(self.get_servers_by_status(status))
        
        return {
            "total_servers": total_servers,
            "active_servers": active_servers,
            "connected_servers": connected_servers,
            "types": type_stats,
            "statuses": status_stats
        }
    
    def get_postgres_tools(self) -> List[Dict[str, Any]]:
        """获取PostgreSQL服务器的工具列表"""
        if not self.postgres_server:
            return []
        
        tools = self.postgres_server.get_tools()
        return [tool.dict() for tool in tools]
    
    async def execute_postgres_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行PostgreSQL工具"""
        if not self.postgres_server:
            return {
                "success": False,
                "error": "PostgreSQL服务器未初始化"
            }
        
        return await self.postgres_server.execute_tool(tool_name, arguments)
