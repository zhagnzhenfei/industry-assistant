import httpx
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status


class MCPAPIService:
    """MCP服务接口调用服务"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    async def get_mcp_servers(self) -> Dict[str, Any]:
        """获取MCP服务列表"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/servers/",
                    params={"include_tools_count": True},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"MCP服务列表获取失败: {response.status_code}"
                    )
                    
        except Exception as e:
            print(f"获取MCP服务列表失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取MCP服务列表失败: {str(e)}"
            )
    
    async def get_server_tools(self, server_id: str) -> Dict[str, Any]:
        """获取指定MCP服务的工具列表"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/servers/{server_id}/tools",
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"获取MCP服务工具列表失败: {response.status_code}"
                    )
                    
        except Exception as e:
            print(f"获取MCP服务工具列表失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取MCP服务工具列表失败: {str(e)}"
            )
    
    async def execute_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行MCP工具"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/servers/{server_id}/tools/{tool_name}/call",
                    json={"arguments": arguments},
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"执行MCP工具失败: {response.status_code}"
                    )
                    
        except Exception as e:
            print(f"执行MCP工具失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"执行MCP工具失败: {str(e)}"
            )
    
    async def get_active_servers(self) -> List[Dict[str, Any]]:
        """获取活跃的MCP服务列表"""
        try:
            servers_data = await self.get_mcp_servers()
            active_servers = []
            
            for server in servers_data.get("servers", []):
                if server.get("status") == "active":
                    active_servers.append({
                        "id": server["id"],
                        "name": server["name"],
                        "description": server["description"],
                        "tools_count": server.get("tools_count", 0),
                        "type": server.get("type"),
                        "tags": server.get("tags", [])
                    })
            
            return active_servers
            
        except Exception as e:
            print(f"获取活跃MCP服务列表失败: {e}")
            return []
    
    async def get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """获取指定MCP服务的详细信息"""
        try:
            servers_data = await self.get_mcp_servers()
            
            for server in servers_data.get("servers", []):
                if server["id"] == server_id:
                    return {
                        "id": server["id"],
                        "name": server["name"],
                        "description": server["description"],
                        "status": server.get("status"),
                        "tools_count": server.get("tools_count", 0),
                        "type": server.get("type"),
                        "tags": server.get("tags", [])
                    }
            
            return None
            
        except Exception as e:
            print(f"获取MCP服务信息失败: {e}")
            return None
